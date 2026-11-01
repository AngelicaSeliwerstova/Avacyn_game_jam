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
from support_story import finish_conversation, read_document
from test_act_one import advance_scene
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
        scene = campaign.load_level("act1")
        advance_scene(scene.session)
        self.addCleanup(scene.session.release)
        scene.player.body._position = glm.vec3(-3, 0, 2.4)
        scene.session.update(0)
        advance_scene(scene.session)
        cabinet = next(o for o in scene.level.objects if o.name == "security_lost_items")
        scene.player._interactions._activate(cabinet)
        scene.session.update(0)
        advance_scene(scene.session)
        return campaign, scene

    def open(self, scene):
        monitor = next(o for o in scene.level.objects if o.name == "security_archive")
        scene.player._interactions._activate(monitor)
        scene.session.update(0)
        finish_conversation(scene.session)
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
        for _ in range(3000):
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
            puzzle.progress.watched = puzzle.progress.aftermath_done = True
            puzzle.save()
            self.addCleanup(puzzle.release)
            for resume in (False, True):
                with self.subTest(resume=resume), patch("main.CCTVProgressStore", side_effect=lambda _, **kw: CCTVProgressStore(path, **kw)), patch("main.Application") as application:
                    application.return_value.run.return_value = "quit"
                    run_session(level_name="act1", resume_archive=resume)
                    session = application.call_args.kwargs["session"]
                    self.addCleanup(session.release)
                    advance_scene(session)
                    self.assertEqual("archive_puzzle_solved" in session._flags, resume)
                    self.assertEqual("archive_recording_watched" in session._flags, resume)
                    if resume:
                        self.assertEqual(session.dialog.title, "КОНЕЦ АКТА 2")
                    else:
                        self.assertIsNone(session.dialog)
                        self.assertFalse(session._puzzles["cctv_archive"].progress.solved)

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

        with patch("sys.argv", ["main.py", "--level", "act1", "--resume-archive"]), \
                patch("main.run_session", side_effect=("restart", "quit")) as run:
            main()
        self.assertEqual(run.call_count, 2)
        self.assertTrue(run.call_args_list[0].kwargs["resume_archive"])
        self.assertFalse(run.call_args_list[1].kwargs["resume_archive"])
        self.assertTrue(all(call.kwargs["level_name"] == "act1" for call in run.call_args_list))

    def test_watched_recording_completes_act_without_report_or_early_revelation(self):
        campaign, scene = self.scene()
        session = scene.session
        self.open(scene)
        self.solve(session)
        self.watch(session)
        self.assertIn("archive_recording_watched", campaign.progress.flags)
        self.assertIn("Кулон", session.dialog.message)
        self.assertNotIn("Это я", session.dialog.message)
        advance_scene(session)
        self.assertIn("act1:complete", session._flags)
        self.assertNotIn("incident_report_read", session._flags)
        self.assertEqual(session.dialog.title, "КОНЕЦ АКТА 2")
        saved = campaign.puzzle_store.get("cctv_archive", self.definition)
        self.assertTrue(saved.solved and saved.watched and saved.aftermath_done)
        restored = Campaign(puzzle_store=campaign.puzzle_store).load_level("act1")
        self.addCleanup(restored.session.release)
        advance_scene(restored.session)
        self.assertEqual(restored.session.dialog.title, "КОНЕЦ АКТА 2")
        beginning = Campaign(puzzle_store=campaign.puzzle_store).load_level("peaceful")
        self.addCleanup(beginning.session.release)
        self.assertNotIn("archive_recording_watched", beginning.session._flags)

    def test_second_act_ending_continues_in_place_into_final_act(self):
        scene = Campaign().load_level("act1")
        self.addCleanup(scene.session.release)
        session = scene.session
        advance_scene(session)
        position = tuple(scene.player.body.position)
        session._prepend(session.act, [{"type": "complete_act"}, {"type": "end", "title": "КОНЕЦ АКТА 2", "text": ""}])
        session._advance()
        self.assertTrue(session.handle_action("story_continue"))
        self.assertEqual(session.act.id, "act2")
        self.assertEqual(tuple(scene.player.body.position), position)
        advance_scene(session)
        self.assertIn("Вернуться к лестнице", scene.player.objective_status)

    def test_recording_keeps_attacker_anonymous_until_final_act(self):
        puzzle = self.puzzle()
        self.addCleanup(puzzle.release)
        puzzle.progress.order = list("ABCD")
        puzzle.check()
        puzzle.play()
        seen = []
        previous = None
        for _ in range(3000):
            view = puzzle.view()
            pair = view.speaker, view.caption
            if pair != previous and view.caption:
                seen.append(pair)
            previous = pair
            if puzzle.tick(.25):
                break
        self.assertTrue(puzzle.progress.watched)
        self.assertTrue(any("Авацин" in text for _, text in seen))
        self.assertTrue(any("Я должна тебя спасти" in text for _, text in seen))
        self.assertTrue(all(speaker != "Героиня" for speaker, _ in seen))
        self.assertTrue(all(speaker.startswith(("Подруга", "Неизвестная")) for speaker, _ in seen))

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
        app._menu = None
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

    def test_mouse_drag_swaps_frames_on_release(self):
        _, scene = self.scene()
        self.open(scene)
        app = Application.__new__(Application)
        app._menu = None
        app._session, app._inventory_open = scene.session, False
        app._render_size, app._input_bindings = (640, 480), controls.INPUT_BINDINGS
        app._running, app._debug_mode = True, False
        cards, _ = archive_layout(scene.session.puzzle_view, (640, 480))
        events = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=cards[0].center),
                  pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=cards[1].center)]
        with patch('pygame.event.get', return_value=events):
            app._handle_events(Mock(), Mock(size=(640, 480)))
        self.assertEqual(scene.session._puzzle.progress.order, list('ACDB'))
        self.assertIsNone(scene.session._puzzle.selected)

    def test_synthesized_recording_speech_stays_off_with_game_audio_enabled(self):
        puzzle = self.puzzle()
        puzzle.data['speech_enabled'] = True
        self.addCleanup(puzzle.release)
        puzzle._sounds = Mock()
        puzzle._voice = Mock()
        puzzle.progress.order = list('ABCD')
        with patch.object(settings, 'AUDIO_ENABLED', True):
            puzzle.check()
            puzzle.play()
            for _ in range(3000):
                if puzzle.tick(.25):
                    break
        self.assertTrue(puzzle.progress.watched)
        puzzle._voice.play.assert_called()
        puzzle._sounds.play_voice.assert_not_called()


if __name__ == "__main__":
    unittest.main()
