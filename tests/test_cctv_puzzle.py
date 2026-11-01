import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import glm
import pygame

from config import controls, settings
from engine.core.application import Application
from engine.rendering.cctv_overlay import CCTVOverlay, archive_action_at, archive_layout
from engine.scene.camera import Camera
from game.campaign import Campaign
from game.puzzles.cctv_puzzle import CCTVPuzzle, CCTVProgressStore, load_cctv_definition
from game.story_loader import load_story
from game.ui import create_hud_style
from support_story import finish_conversation
from test_hospital import walk


class CCTVTests(unittest.TestCase):
    def setUp(self):
        self.mute = patch.object(settings, "AUDIO_ENABLED", False)
        self.mute.start()
        self.addCleanup(self.mute.stop)
        self.book = load_story("hospital")
        self.definition = load_cctv_definition("cctv/archive.json", self.book.data["characters"])

    def puzzle(self, store=None):
        return CCTVPuzzle("cctv_archive", self.definition, store or CCTVProgressStore(), self.book.data["characters"])

    def scene(self, store=None):
        campaign = Campaign(puzzle_store=store)
        scene = campaign.load_level("act2")
        scene.session.tick_presentation(4)
        finish_conversation(scene.session)
        self.addCleanup(scene.session.release)
        return campaign, scene

    def open(self, scene):
        monitor = next(o for o in scene.level.objects if o.name == "security_archive")
        scene.player._interactions._activate(monitor)
        scene.session.update(0)
        self.assertTrue(scene.session.puzzle_active)

    def solve(self, session):
        for target, frame in enumerate(self.definition["correct_order"]):
            current = session._puzzle.progress.order.index(frame)
            if target != current:
                session.handle_puzzle_action(f"archive_frame:{target}")
                session.handle_puzzle_action(f"archive_frame:{current}")
        session.handle_puzzle_action("archive_check")

    def watch(self, session):
        if not session._puzzle.playing:
            session.handle_puzzle_action("archive_play")
        for _ in range(500):
            session.tick_presentation(0.1)
            if not session.puzzle_active:
                session.update(0)
                return
        self.fail("Recording never ended")

    def test_only_one_of_24_orders_is_correct_and_failure_has_no_penalty(self):
        for order in itertools.permutations("ABCD"):
            puzzle = self.puzzle()
            puzzle.progress.order = list(order)
            self.assertEqual(puzzle.check(), order == tuple("ABCD"))
            self.assertEqual(puzzle.progress.order, list(order))
        puzzle = self.puzzle()
        puzzle.hint()
        self.assertEqual(puzzle.message, "")
        puzzle.check()
        puzzle.check()
        self.assertTrue(puzzle.view().hint_available)
        puzzle.hint()
        self.assertIn(self.definition["hint"], puzzle.message)
        self.assertEqual(puzzle.progress.order, list("CADB"))
        puzzle.click(0)
        puzzle.click(0)
        self.assertIsNone(puzzle.selected)
        puzzle.click(0)
        puzzle.click(1)
        self.assertEqual(puzzle.progress.order, list("ACDB"))
        puzzle.reset()
        self.assertEqual(puzzle.progress.order, list("CADB"))
        self.assertEqual(puzzle.progress.attempts, 2)

    def test_escape_order_and_checkpoints_survive_new_campaign_and_disk_store(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.json"
            store = CCTVProgressStore(path)
            _, scene = self.scene(store)
            self.open(scene)
            scene.session.handle_puzzle_action("archive_frame:0")
            scene.session.handle_puzzle_action("archive_frame:1")
            scene.session.handle_puzzle_action("archive_close")
            self.assertFalse(scene.session.puzzle_active)
            self.assertIsNone(scene.session.dialog)
            _, restored = self.scene(CCTVProgressStore(path))
            self.open(restored)
            self.assertEqual(restored.session._puzzle.progress.order, list("ACDB"))
            self.assertFalse(restored.session.handle_gameplay_key("m"))
            self.solve(restored.session)
            self.assertTrue(restored.session.puzzle_view.solved)
            self.assertIn("archive_puzzle_solved", restored.session._flags)
            order = list(restored.session._puzzle.progress.order)
            restored.session.handle_puzzle_action("archive_frame:0")
            restored.session.handle_puzzle_action("archive_reset")
            self.assertEqual(restored.session._puzzle.progress.order, order)
            restored.session.handle_puzzle_action("archive_close")
            self.open(restored)
            self.assertTrue(restored.session.puzzle_view.playing)
            restored.session.handle_puzzle_action("archive_close")
            self.assertNotIn("archive_recording_watched", restored.session._flags)

    def test_new_session_starts_unsolved_and_only_explicit_resume_restores_checkpoint(self):
        from main import run_session

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.json"
            puzzle = self.puzzle(CCTVProgressStore(path))
            puzzle.progress.order = list(self.definition["correct_order"])
            puzzle.check()
            puzzle.progress.watched = puzzle.progress.report_read = puzzle.progress.aftermath_done = True
            puzzle.save()
            self.addCleanup(puzzle.release)

            for resume in (False, True):
                with self.subTest(resume=resume), \
                        patch("main.CCTVProgressStore", side_effect=lambda _, **kwargs: CCTVProgressStore(path, **kwargs)), \
                        patch("main.Application") as application:
                    application.return_value.run.return_value = "quit"
                    run_session(level_name="act2", **({"resume_archive": True} if resume else {}))
                    session = application.call_args.kwargs["session"]
                    self.addCleanup(session.release)
                    self.assertEqual("archive_puzzle_solved" in session._flags, resume)
                    self.assertEqual(session.player.inventory.has_item("incident_report"), resume)
                    session.tick_presentation(4)
                    finish_conversation(session)
                    monitor = next(o for o in application.call_args.kwargs["level"].objects
                                   if o.name == "security_archive")
                    session.player._interactions._activate(monitor)
                    session.update(0)
                    self.assertTrue(session.puzzle_active)
                    self.assertEqual(session.puzzle_view.solved, resume)
                    self.assertEqual(session._puzzle.progress.order,
                                     self.definition["correct_order"] if resume else self.definition["initial_order"])

    def test_fresh_disk_store_saves_current_run_and_reopening_monitor_keeps_its_order(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.json"
            previous = self.puzzle(CCTVProgressStore(path))
            previous.progress.order = list(self.definition["correct_order"])
            previous.check()
            self.addCleanup(previous.release)

            store = CCTVProgressStore(path, resume=False)
            _, scene = self.scene(store)
            self.open(scene)
            scene.session.handle_puzzle_action("archive_frame:0")
            scene.session.handle_puzzle_action("archive_frame:1")
            scene.session.handle_puzzle_action("archive_close")
            self.open(scene)
            self.assertEqual(scene.session._puzzle.progress.order, list("ACDB"))
            self.assertFalse(scene.session.puzzle_view.solved)
            saved = CCTVProgressStore(path).get("cctv_archive", self.definition)
            self.assertEqual(saved.order, list("ACDB"))
            self.assertFalse(saved.solved or saved.watched or saved.report_read or saved.aftermath_done)

    def test_restart_starts_fresh_even_when_launching_with_saved_archive(self):
        from main import main

        with patch("sys.argv", ["main.py", "--level", "act2", "--resume-archive"]), \
                patch("main.run_session", side_effect=("restart", "quit")) as run:
            main()
        self.assertEqual(run.call_count, 2)
        self.assertTrue(run.call_args_list[0].kwargs["resume_archive"])
        self.assertFalse(run.call_args_list[1].kwargs["resume_archive"])
        self.assertTrue(all(call.kwargs["level_name"] == "act2" for call in run.call_args_list))

    def test_full_story_all_choices_unlock_report_and_dialogue_only_once(self):
        for choice in range(3):
            with self.subTest(choice=choice):
                campaign, scene = self.scene()
                session = scene.session
                report = next(o for o in scene.level.objects if o.name == "incident_report")
                self.assertIsNone(report.interaction)
                self.open(scene)
                self.solve(session)
                self.assertIsNone(report.interaction)
                self.watch(session)
                self.assertIn("archive_recording_watched", campaign.progress.flags)
                self.assertEqual(session.dialog.message, session.act.dialogues["after_recording"][0]["text"])
                finish_conversation(session, choice)
                self.assertIn(f"act2:choice:recognition:{choice}", session._flags)
                self.assertIsNotNone(report.interaction)
                scene.player._interactions._activate(report)
                session.update(0)
                self.assertEqual(session.dialog.presentation, "document")
                self.assertIn("она погибла", " ".join(session._document_pages))
                while "document_next" in {b.action for b in session.dialog.buttons}:
                    session.handle_action("document_next")
                session.handle_action("document_close")
                finish_conversation(session)
                self.assertTrue({"archive_puzzle_solved", "archive_recording_watched", "incident_report_read"} <= session._flags)
                self.assertIn("Архив изучен", scene.player.objective_status)
                self.open(scene)
                self.watch(session)
                self.assertIsNone(session.dialog)
                saved = campaign.puzzle_store.get("cctv_archive", self.definition)
                self.assertTrue(saved.solved and saved.watched and saved.report_read and saved.aftermath_done)
                restored = campaign.load_level("act2")
                self.assertIsNotNone(next(o for o in restored.level.objects if o.name == "incident_report").interaction)
                fresh = Campaign(puzzle_store=campaign.puzzle_store).load_level("act2")
                self.assertIsNotNone(next(o for o in fresh.level.objects if o.name == "incident_report").interaction)
                beginning = Campaign(puzzle_store=campaign.puzzle_store).load_level("peaceful")
                self.assertNotIn("incident_report_read", beginning.session._flags)
                self.assertFalse(beginning.player.inventory.has_item("incident_report"))

    def test_act_one_ending_continues_in_place_into_act_two(self):
        campaign = Campaign()
        scene = campaign.load_level("act1")
        session = scene.session
        session.tick_presentation(4)
        finish_conversation(session)
        position = tuple(scene.player.body.position)
        session._prepend(session.act, [{"type": "complete_act"}, {"type": "end", "title": "КОНЕЦ АКТА 1", "text": ""}])
        session._advance()
        self.assertTrue(session.handle_action("story_continue"))
        self.assertEqual(session.act.id, "act2")
        self.assertEqual(session.dialog.presentation, "title")
        self.assertEqual(tuple(scene.player.body.position), position)
        session.tick_presentation(4)
        finish_conversation(session)
        self.assertIn("Изучить записи камер", scene.player.objective_status)

    def test_hero_says_the_line_before_unknown_voice_and_escape_never_marks_watched(self):
        puzzle = self.puzzle()
        puzzle.progress.order = list("ABCD")
        puzzle.check()
        puzzle.play()
        seen = []
        previous = None
        for _ in range(500):
            view = puzzle.view()
            pair = view.speaker, view.caption
            if pair != previous and view.caption:
                seen.append(pair)
            previous = pair
            if puzzle.tick(0.1):
                break
        hero = next(i for i, (speaker, text) in enumerate(seen) if speaker == "Героиня" and "Оставь" in text)
        unknown = next(i for i, (speaker, text) in enumerate(seen) if speaker.startswith("Неизвестная") and "Оставь" in text)
        self.assertLess(hero, unknown)
        self.assertTrue(puzzle.progress.watched)

    def test_monitor_and_report_are_physically_visible_from_security_room(self):
        _, scene = self.scene()
        for name in ("security_0", "security_hall_0"):
            door = next(o for o in scene.level.objects if o.name == name)
            door.set_state("open")
            door.update(1)
        scene.player.body._position = glm.vec3(-3, 0, -2)
        walk(self, scene.player.body, ((-3, 0, 1.5), (-1.8, 0, 3.6)), fps=20)
        for name, position in (("security_archive", (-1.8, 0, 3.6)), ("incident_report", (-4.1, 0, 3.6))):
            obj = next(o for o in scene.level.objects if o.name == name)
            if name == "incident_report":
                obj.set_state("default")
            scene.player.body._position = glm.vec3(position)
            self.assertFalse(scene.player.body.world.is_blocked(glm.vec3(position), 0.25, 1.8))
            eye = tuple(scene.player.body.eye_position(settings.PLAYER_EYE_HEIGHT))
            target = obj.current_state.selection_box or obj.boxes[0]
            scene.player._interactions.update(0, Camera(eye, target.position, 65, 0.1, 150), reach_origin=eye)
            self.assertIs(scene.player._interactions.focused, obj)

    def test_mouse_mapping_and_app_pause_close_restore_capture(self):
        _, scene = self.scene()
        self.open(scene)
        view = scene.session.puzzle_view
        cards, buttons = archive_layout(view, (640, 480))
        for i, rect in enumerate(cards):
            point = (192 + rect.centerx * 1.8, rect.centery * 1.8)
            self.assertEqual(archive_action_at(view, point, (1536, 864), (640, 480)), f"archive_frame:{i}")
        self.assertIsNone(archive_action_at(view, (0, 10), (1536, 864), (640, 480)))
        app = Application.__new__(Application)
        app._session, app._inventory_open = scene.session, False
        app._render_size, app._input_bindings = (640, 480), controls.INPUT_BINDINGS
        app._running, app._debug_mode = True, False
        self.assertTrue(app._simulation_paused)
        device = Mock()
        with patch("pygame.event.get", return_value=[pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)]):
            app._handle_events(device, Mock(size=(640, 480)))
        self.assertFalse(app._simulation_paused)
        device.end_modal.assert_called_once()

    def test_corrupt_checkpoint_falls_back_without_breaking_the_level(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "archive.json"
            for text in ("{", '{"version": 12}', '{"version": 1, "puzzles": {"cctv_archive": {"order": [[], 1, 2, 3]}}}'):
                path.write_text(text, encoding="utf-8")
                puzzle = self.puzzle(CCTVProgressStore(path))
                self.assertEqual(puzzle.progress.order, list("CADB"))
                self.assertFalse(puzzle.progress.solved)


if __name__ == "__main__":
    unittest.main()
