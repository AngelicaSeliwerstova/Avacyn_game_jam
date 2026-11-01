from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from config import settings
from game.campaign import Campaign
from game.levels.patient_archive import ARCHIVE_DRAWER_ID
from game.levels.story_props import StoryPropSystem
from game.story_loader import STORY_ROOT, StoryFormatError, load_story
from support_story import finish_conversation, read_document


class StoryResourceTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        shutil.copytree(STORY_ROOT / "hospital", self.root / "hospital")
        self.campaign = self.root / "hospital/campaign.json"
        self.act = self.root / "hospital/acts/act0/act.json"
        self.dialogue = self.act.with_name("dialogue.json")
        self.documents = self.act.with_name("documents.json")
        root_patch = patch("game.story_loader.STORY_ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        audio = patch.object(settings, "AUDIO_ENABLED", False)
        audio.start()
        self.addCleanup(audio.stop)

    def edit(self, path, mutate):
        data = json.loads(path.read_text(encoding="utf-8"))
        mutate(data)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_external_dialogue_choices_names_objectives_and_transition_are_used(self):
        def dialogue(data):
            data["meeting"] = [{"speaker": "doctor", "text": "Это изменено только в JSON."},
                               {"choice": "edited", "speaker": "hero", "prompt": "Новый вопрос?", "options": [
                                   {"label": "Новый ответ", "set_flags": ["custom_answer"],
                                    "lines": [{"speaker": "hero", "text": "Изменённая ветка."}]}]}]
        self.edit(self.dialogue, dialogue)
        self.edit(self.campaign, lambda data: data["characters"]["doctor"].update(name="Анна"))
        def act(data):
            data["objectives"][0]["title"] = "Новая задача"
            next(scene for scene in data["scenes"] if scene["id"] == "intro")["steps"][0]["seconds"] = 0.25
            next(scene for scene in data["scenes"] if scene["id"] == "meeting")["steps"][-1]["level"] = "peaceful"
        self.edit(self.act, act)
        scene = Campaign().load_level("peaceful")
        session = scene.session
        self.assertIn("Новая задача", scene.player.objective_status)
        session.tick_presentation(0.25)
        finish_conversation(session)
        session.actors["doctor"].request_talk()
        session.update(0)
        self.assertEqual(session.dialog.title, "Анна")
        self.assertEqual(session.actors["doctor"].scene_object.interaction.name, "Анна")
        self.assertEqual(session.dialog.message, "Это изменено только в JSON.")
        session.reveal_dialogue()
        session.handle_action("story_next")
        self.assertEqual(session.dialog.message, "Новый вопрос?")
        self.assertEqual(len(session.dialog.buttons), 1)
        session.handle_action("story_choice:0")
        self.assertEqual(session.dialog.message, "Изменённая ветка.")
        finish_conversation(session)
        read_document(session)
        session.tick_presentation(1.8)
        session.tick_presentation(2.2)
        self.assertIn("custom_answer", session._flags)
        self.assertEqual(session.next_level, "peaceful")

    def test_documents_can_change_length_and_optional_reading_rules(self):
        def documents(data):
            data["mother_letter"]["pages"] = ["Единственная новая страница."]
            data["mother_letter"]["title"] = "Новая записка"
            data["hospital_plan"]["require_all_floors"] = False
        self.edit(self.documents, documents)
        session = Campaign().load_level("start").session
        finish_conversation(session)
        session.open_document("hospital_plan")
        self.assertTrue(session.handle_action("map_close"))
        finish_conversation(session)
        self.assertIsNone(session.dialog)
        session._flags.update(("act0:archive_card_read", "act0:assessment_read"))
        session._files.show()
        session.handle_action("files_year:1981")
        session.handle_action("files_case")
        session.handle_action("files_letter")
        self.assertEqual(session.dialog.title, "Новая записка · 1 / 1")
        self.assertEqual(session.dialog.message, "Единственная новая страница.")
        self.assertTrue(session.handle_action("document_close"))
        finish_conversation(session)
        self.assertIn("act0:archive_reviewed", session._flags)
        self.assertNotIn("act0:complete", session._flags)

    def test_second_act_is_enabled_and_started_entirely_from_resources(self):
        self.edit(self.act, lambda data: data.update(next_act="act1"))
        self.edit(self.act, lambda data: data["scenes"].append({"id": "custom_next", "trigger":
            {"type": "event", "name": "act_complete:act0"}, "requires": ["act0:complete"],
            "steps": [{"type": "next_act"}]}))
        self.edit(self.campaign, lambda data: data["acts"][1].update(enabled=True))
        next_path = self.act.parent.parent / "act1/act.json"
        self.edit(next_path.with_name("dialogue.json"), lambda data: data.update({
            "start": [{"speaker": "doctor", "text": "Начало второго акта из файла."}]}))
        def act(data):
            data["objectives"] = [{"title": "Задача второго акта", "description": "Описание из файла."}]
            data["scenes"] = [{"id": "arrival", "trigger": {"type": "load"},
                               "steps": [{"type": "dialogue", "id": "start"}]}]
        self.edit(next_path, act)
        campaign = Campaign()
        scene = campaign.load_level("start")
        session = scene.session
        finish_conversation(session)
        campaign.progress.flags.add("act0:complete")
        scene.player.story_events.add("act_complete:act0")
        session.update(0)
        for _ in range(20):
            if session.act.id != "act0":
                break
            session.reveal_dialogue()
            session.handle_action(session.dialog.buttons[0].action)
        self.assertEqual(session.act.id, "act1")
        self.assertEqual(session.dialog.message, "Начало второго акта из файла.")
        self.assertIn("Задача второго акта", scene.player.objective_status)
        finish_conversation(session)
        reloaded = campaign.load_level("start")
        self.assertEqual(reloaded.session.act.id, "act1")
        self.assertIsNone(reloaded.session.dialog)

    def test_zone_changes_and_reordered_steps_change_scene_behavior(self):
        def act(data):
            meeting = data["scenes"][1]
            meeting["trigger"] = {"type": "zone", "zone": "office"}
            data["zones"]["office"] = {"min": [-2, -0.5, 11], "max": [2, 0.5, 13]}
            meeting["steps"] = [{"type": "flags", "add": ["custom_scene"]},
                                {"type": "dialogue", "id": "reception"}]
        self.edit(self.act, act)
        session = Campaign().load_level("peaceful").session
        session.tick_presentation(4)
        finish_conversation(session)
        session.update(0)
        self.assertIn("custom_scene", session._flags)
        self.assertEqual(session.dialog.message, session.act.dialogues["reception"][0]["text"])

    def test_reference_and_format_errors_identify_the_file_and_field(self):
        cases = [
            (self.dialogue, lambda data: data["meeting"][0].update(speaker="missing"), "speaker"),
            (self.dialogue, lambda data: data["after_letter"][2].update(options=[]), "options"),
            (self.dialogue, lambda data: data["cradle_memory"][0].update(audio="../outside.wav"), "inside"),
            (self.dialogue, lambda data: data["cradle_memory"][0].update(seconds=-1), "seconds"),
            (self.act, lambda data: data["scenes"][-4]["steps"].append({"type": "ambience", "gain": 2, "seconds": 1}), "gain"),
            (self.documents, lambda data: data["mother_letter"].update(pages=[]), "pages"),
            (self.act, lambda data: data["scenes"][0]["steps"].append({"type": "python", "code": "pass"}), "unknown step"),
            (self.act, lambda data: data["scenes"][1].update(trigger={"type": "zone", "zone": "missing"}), "zone"),
            (self.act, lambda data: data["scenes"][0].update(requires="not_a_list"), "requires"),
            (self.act, lambda data: data.update(dialogues_file="../dialogue.json"), "inside"),
            (self.campaign, lambda data: data.update(start_act="missing"), "start act"),
            (self.act, lambda data: data["scenes"].append(deepcopy(data["scenes"][0])), "duplicate scene"),
        ]
        for path, mutate, message in cases:
            with self.subTest(message=message):
                original = path.read_text(encoding="utf-8")
                try:
                    self.edit(path, mutate)
                    with self.assertRaises(StoryFormatError) as error:
                        load_story("hospital", self.root)
                    self.assertIn(message, str(error.exception))
                    self.assertIn(str(path.parent.resolve()), str(error.exception))
                finally:
                    path.write_text(original, encoding="utf-8")

    def test_invalid_json_and_duplicate_keys_are_rejected(self):
        for text in ('{"version":', '{"version": 1, "version": 2}'):
            with self.subTest(text=text):
                self.campaign.write_text(text, encoding="utf-8")
                with self.assertRaises(StoryFormatError) as error:
                    load_story("hospital", self.root)
                self.assertIn(str(self.campaign.resolve()), str(error.exception))

    def test_long_authored_text_is_paginated_without_losing_words(self):
        text = "Это длинная изменённая реплика для проверки страниц. " * 100
        self.edit(self.dialogue, lambda data: data.update(meeting=[{"speaker": "doctor", "text": text}]))
        session = Campaign().load_level("peaceful").session
        session.tick_presentation(4)
        finish_conversation(session)
        session.actors["doctor"].request_talk()
        session.update(0)
        pages = []
        for _ in range(200):
            if session.dialog.presentation != "conversation":
                break
            pages.append(session.dialog.message)
            session.reveal_dialogue()
            session.handle_action("story_next")
        self.assertGreater(len(pages), 1)
        self.assertEqual(" ".join(pages).split(), text.split())
        self.edit(self.documents, lambda data: data["mother_letter"].update(pages=[text]))
        session = Campaign().load_level("start").session
        finish_conversation(session)
        session.open_document("mother_letter")
        pages = []
        for _ in range(200):
            pages.append(session.dialog.message)
            if "document_next" not in {button.action for button in session.dialog.buttons}:
                break
            self.assertFalse(session.handle_action("document_close"))
            session.handle_action("document_next")
        self.assertGreater(len(pages), 1)
        self.assertEqual(" ".join(pages).split(), text.split())
        self.assertTrue(session.handle_action("document_close"))


if __name__ == "__main__":
    unittest.main()
