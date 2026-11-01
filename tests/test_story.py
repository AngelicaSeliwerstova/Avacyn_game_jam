import unittest
from unittest.mock import patch

import glm
import pygame

from config import settings
from engine.input.state import InputState
from engine.rendering.dialog import DialogOverlay, dialog_action_at, dialog_button_rects
from engine.scene.camera import Camera
from game.campaign import Campaign
from game.levels.patient_archive import ARCHIVE_DRAWER_ID
from game.levels.story_props import StoryPropSystem
from game.story import StorySession
from game.ui import create_hud_style
from support_story import complete_patient_archive, finish_conversation, read_document, finish_office, finish_memory
from test_hospital import walk


class ActZeroTests(unittest.TestCase):
    def setUp(self):
        self.audio = patch.object(settings, "AUDIO_ENABLED", False)
        self.audio.start()
        self.addCleanup(self.audio.stop)

    def enter_ruined_hospital(self, choice=0):
        campaign = Campaign()
        scene = campaign.load_level("peaceful")
        session = scene.session
        self.assertIsInstance(session, StorySession)
        self.assertEqual(session.dialog.presentation, "title")
        self.assertFalse(session.handle_action("story_next"))
        session.tick_presentation(3)
        self.assertGreater(session.dialog.opacity, 0)
        self.assertLess(session.dialog.opacity, 1)
        session.tick_presentation(1)
        finish_conversation(session)
        self.assertIsNone(session.dialog)
        session.actors["doctor"].request_talk()
        session.update(0)
        self.assertEqual(session.dialog.message.split(), session.act.dialogues["meeting"][0]["text"].split())
        finish_office(session)
        self.assertEqual(session.next_level, "start")
        ruined = campaign.load_level("start")
        self.assertLess(glm.distance(ruined.player.body.position, scene.player.body.position), 1e-5)
        self.assertEqual(tuple(ruined.session.actors["doctor"].body.position), tuple(session.actors["doctor"].body.position))
        self.assertTrue(ruined.session.actors["doctor"].following)
        ruined.session.update(0)
        finish_conversation(ruined.session, choice)
        return campaign, ruined

    def request_document(self, scene, name):
        obj = next(obj for obj in scene.level.objects if obj.name == name)
        scene.player._interactions._activate(obj)
        scene.session.update(0)

    def open_archive(self, scene):
        self.request_document(scene, ARCHIVE_DRAWER_ID)
        self.assertTrue(scene.session.handle_action("files_year:1981"))

    def test_both_letter_responses_reach_cradle_ending_only_after_full_memory(self):
        for choice in range(2):
            with self.subTest(choice=choice):
                campaign, scene = self.enter_ruined_hospital(choice)
                session = scene.session
                self.assertFalse(session.handle_gameplay_key("m"))
                self.assertNotIn("act0:letter_read", campaign.progress.flags)
                self.request_document(scene, "hospital_plan")
                self.assertTrue(session.handle_action("map_close"))
                finish_conversation(session)
                self.assertIsNone(session.dialog)
                complete_patient_archive(session, choice)
                self.assertNotIn("act0:complete", campaign.progress.flags)
                self.assertIn("act0:archive_closed", campaign.progress.flags)
                self.assertTrue(scene.player.inventory.has_key("second_floor_key"))
                self.assertIn("act0:cry_started", session._flags)
                scene.player.story_events.add("locked:f3_patient_ward_313")
                session.update(0)
                self.assertNotIn("act0:complete", session._flags)
                self.request_document(scene, "f2_nursery_cradle")
                self.assertIsNone(session.dialog)
                door = next(o for o in scene.level.objects if o.name == "f2_surgery_preop")
                scene.player._interactions._activate(door)
                session.update(0)
                self.assertIn("act0:cry_stopped", session._flags)
                self.assertIn("act0:nursery_open", session._flags)
                self.assertIsNone(session.dialog)
                self.request_document(scene, "f2_nursery_cradle")
                self.assertEqual(session.dialog.presentation, "distortion")
                session.tick_presentation(1.2)
                self.assertEqual(session.dialog.presentation, "voiceover")
                self.assertFalse(session.handle_action("story_next"))
                self.assertNotIn("act0:complete", session._flags)
                finish_memory(session)
                self.assertIn("act0:complete", campaign.progress.flags)
                self.assertIn(f"act0:choice:letter:{choice}", campaign.progress.flags)
                self.assertIn("act0:memory_heard", session._flags)
                self.assertEqual(session.act.id, "act0")
                self.assertEqual(session.dialog.title, "КОНЕЦ АКТА 1")
                self.assertNotIn("story_continue", {b.action for b in session.dialog.buttons})
                self.assertEqual(scene.player.story_audio_gain, 1)

    def test_office_door_documents_and_reception_are_physically_reachable(self):
        campaign = Campaign()
        scene = campaign.load_level("peaceful")
        session = scene.session
        session.tick_presentation(4)
        finish_conversation(session)
        door = next(obj for obj in scene.level.objects if obj.name == "office_0")
        door.set_state("open")
        door.update(1)
        walk(self, scene.player.body, ((3.5, 0, 12.2), (3.5, 0, -4.5), (-17, 0, -4.5), (-17, 0, -8.4)))
        session.update(0)
        self.assertEqual(session.dialog.presentation, "conversation")
        finish_office(session)
        scene = campaign.load_level("start")
        session = scene.session
        self.assertEqual(next(o for o in scene.level.objects if o.name == "office_0").state_name, "open")
        session.update(0)
        finish_conversation(session)
        walk(self, scene.player.body, ((-17, 0, -4.5), (3.5, 0, -4.5), (3.5, 0, 9.5),
                                      (19.4, 0, 9.5), (19.4, 0, 2.6), (13.4, 0, 2.3)))
        session.update(0)
        finish_conversation(session)
        self.assertIn("act0:reception", campaign.progress.flags)
        scene.player.update(0, InputState(interact=True))
        self.assertEqual(scene.player._interactions.focused.name, "hospital_plan")
        session.update(0)
        session.handle_action("map_next")
        session.handle_action("map_next")
        session.handle_action("map_close")
        finish_conversation(session)
        self.assertIsNone(session.dialog)
        self.request_document(scene, "archive_card")
        read_document(session)
        walk(self, scene.player.body, ((9.52, 0, 3.0),))
        drawer = next(o for o in scene.level.objects if o.name == ARCHIVE_DRAWER_ID)
        eye = tuple(scene.player.body.eye_position(settings.PLAYER_EYE_HEIGHT))
        camera = Camera(eye, drawer.current_state.selection_box.position, 65, 0.1, 150)
        scene.player._interactions.update(0, camera, pressed=True, reach_origin=eye)
        self.assertIs(scene.player._interactions.focused, drawer)
        session.update(0)
        self.assertTrue(session.handle_action("files_year:1981"))
        session.handle_action("files_close")
        drawer.update(1)
        next(s for s in scene.systems if isinstance(s, StoryPropSystem)).update(0)
        case = next(o for o in scene.level.objects if o.name == "archive_case_081")
        camera.target = glm.vec3(case.current_state.selection_box.position)
        scene.player._interactions.update(0, camera, pressed=True, reach_origin=eye)
        self.assertIn(scene.player._interactions.focused.name, (ARCHIVE_DRAWER_ID, "archive_case_081"))
        session.update(0)
        self.assertEqual(session.dialog.presentation, "filing_archive")
        self.assertEqual(drawer.state_name, "open")
        self.assertTrue(case.boxes)

    def test_plan_and_letter_render_and_click_at_scaled_window_sizes(self):
        pygame.font.init()
        scene = Campaign().load_level("start")
        session = scene.session
        overlay = DialogOverlay.__new__(DialogOverlay)
        overlay._style = create_hud_style()
        overlay._font = pygame.font.Font(str(overlay._style.font_path), 18)
        overlay._title_font = pygame.font.Font(str(overlay._style.font_path), 28)
        for page in range(3):
            session.open_document("mother_letter", page)
            self.check_document(overlay, session.dialog)
            session.open_document("hospital_plan", page)
            self.assertTrue(session.dialog.plan_walls)
            self.check_document(overlay, session.dialog)

    def check_document(self, overlay, dialog):
        surface = pygame.Surface((640, 480), pygame.SRCALPHA)
        overlay._draw_document(surface, dialog, (640, 480), None)
        self.assertEqual(surface.get_at((320, 240)).a, 255)
        for button, rect in zip(dialog.buttons, dialog_button_rects(dialog, (640, 480))):
            point = (192 + rect.centerx * 1.8, rect.centery * 1.8)
            self.assertEqual(dialog_action_at(dialog, point, (1536, 864), (640, 480)), button.action)


if __name__ == "__main__":
    unittest.main()
