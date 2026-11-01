import unittest
from unittest.mock import patch

import glm
from engine.scene.camera import Camera
from engine.input.state import InputState

from config import settings
from game.campaign import Campaign
from game.levels.patient_archive import (ARCHIVE_DRAWER_ID, ARCHIVE_LETTER_POSITION, ARCHIVE_OPEN_FLAG,
                                        ARCHIVE_YEARS, DRAWER_TRAVEL)
from game.levels.story_props import StoryPropSystem
from game.puzzles.patient_files import REQUIRED_FLAGS
from engine.rendering.dialog import DialogOverlay, dialog_action_at, dialog_button_rects
from game.ui import create_hud_style
import pygame
from support_story import complete_patient_archive, finish_conversation, read_document
from test_hospital import make_body


class PatientArchiveTests(unittest.TestCase):
    def setUp(self):
        mute = patch.object(settings, "AUDIO_ENABLED", False)
        mute.start()
        self.addCleanup(mute.stop)

    def scene(self):
        campaign = Campaign()
        scene = campaign.load_level("start")
        scene.session.update(0)
        finish_conversation(scene.session)
        self.addCleanup(scene.session.release)
        return campaign, scene

    def objects(self, scene):
        return {obj.name: obj for obj in scene.level.objects}

    def test_cabinet_has_dated_drawers_and_letter_is_hidden_in_every_fresh_map(self):
        for name in ("peaceful", "start"):
            scene = Campaign().load_level(name)
            self.addCleanup(scene.session.release)
            objects = self.objects(scene)
            self.assertTrue(all(f"patient_archive_{year}" in objects for year in ARCHIVE_YEARS))
            self.assertEqual(objects[ARCHIVE_DRAWER_ID].state_name, "default")
            letter = objects["mother_letter"]
            self.assertEqual(letter.state_name, "hidden")
            self.assertFalse(letter.boxes)
            self.assertIsNone(letter.interaction)
            self.assertEqual(letter.states["default"].boxes[0].position, ARCHIVE_LETTER_POSITION)

    def test_drawer_opens_without_plan_and_reveals_folder_after_animation_without_modal_lock(self):
        _, scene = self.scene()
        session = scene.session
        drawer, case = (self.objects(scene)[name] for name in (ARCHIVE_DRAWER_ID, "archive_case_081"))
        props = next(s for s in scene.systems if isinstance(s, StoryPropSystem))
        scene.player._interactions._activate(drawer)
        session.update(0)
        self.assertNotIn("act0:map", session._flags)
        self.assertEqual(session.dialog.presentation, "filing_archive")
        self.assertTrue(session.handle_action("files_year:1981"))
        self.assertTrue(drawer.transitioning)
        self.assertIsNone(drawer.interaction)
        self.assertFalse(session.controls_locked)
        self.assertIn(ARCHIVE_OPEN_FLAG, session._flags)
        props.update(0)
        self.assertEqual(case.state_name, "hidden")
        drawer.update(1)
        props.update(0)
        self.assertEqual(case.state_name, "default")
        self.assertAlmostEqual(drawer.boxes[0].position[2] - drawer.states["default"].boxes[0].position[2], DRAWER_TRAVEL)
        self.assertNotIn("act0:complete", session._flags)

    def test_opening_pauses_at_player_and_continues_after_stepping_back(self):
        _, scene = self.scene()
        drawer = self.objects(scene)[ARCHIVE_DRAWER_ID]
        scene.player.body = make_body(scene.player.body.world, (9.52, 0, 1.9))
        scene.session._flags.update(("act0:map", "act0:reception"))
        scene.player._interactions._activate(drawer)
        scene.session.update(0)
        scene.session.handle_action("files_year:1981")
        scene.session.handle_action("files_close")
        drawer.update(1)
        self.assertTrue(drawer.transitioning)
        self.assertFalse(scene.session.controls_locked)
        self.assertFalse(scene.player.body.world.is_blocked(scene.player.body.position, 0.249, 1.799))
        scene.player.body._position = glm.vec3(9.52, 0, 3)
        drawer.update(1)
        next(s for s in scene.systems if isinstance(s, StoryPropSystem)).update(0)
        self.assertFalse(drawer.transitioning)
        self.assertEqual(self.objects(scene)["archive_case_081"].state_name, "default")

    def test_reloading_preserves_open_drawer_and_new_campaign_starts_closed(self):
        campaign, scene = self.scene()
        campaign.progress.flags.add(ARCHIVE_OPEN_FLAG)
        restored = campaign.load_level("start")
        self.addCleanup(restored.session.release)
        objects = self.objects(restored)
        self.assertEqual(objects[ARCHIVE_DRAWER_ID].state_name, "open")
        self.assertFalse(objects[ARCHIVE_DRAWER_ID].transitioning)
        self.assertEqual(objects["archive_case_081"].state_name, "default")
        fresh = Campaign().load_level("start")
        self.addCleanup(fresh.session.release)
        self.assertEqual(self.objects(fresh)[ARCHIVE_DRAWER_ID].state_name, "default")
        self.assertEqual(self.objects(fresh)["mother_letter"].state_name, "hidden")

    def test_exact_five_years_and_wrong_years_are_optional_and_do_not_complete_archive(self):
        _, scene = self.scene()
        session = scene.session
        self.assertEqual(ARCHIVE_YEARS, (1975, 1978, 1981, 1985, 1990))
        session._files.show()
        for year in ARCHIVE_YEARS:
            self.assertTrue(session.handle_action(f"files_year:{year}"))
            if year != 1981:
                self.assertTrue(session.handle_action("files_misc:1"))
                self.assertEqual(session.dialog.presentation, "document")
                self.assertIn(str(year), session.dialog.message)
                self.assertTrue(session.handle_action("files_return"))
            else:
                self.assertTrue(session.handle_action("files_case"))
                self.assertIn("act0:case_081_open", session._flags)
                self.assertNotIn("act0:archive_card_read", session._flags)
            session.handle_action("files_back")
        session.handle_action("files_close")
        self.assertNotIn("act0:archive_closed", session._flags)
        self.assertNotIn("act0:complete", session._flags)

    def test_all_required_documents_and_dialogue_are_needed_before_finishing(self):
        _, scene = self.scene()
        session = scene.session
        session._flags.add("act0:map")
        complete_patient_archive(session)
        self.assertTrue(REQUIRED_FLAGS <= session._flags)
        self.assertIn("act0:archive_closed", session._flags)
        self.assertNotIn("act0:complete", session._flags)
        for missing in REQUIRED_FLAGS:
            with self.subTest(missing=missing):
                session._flags.discard("act0:archive_closed")
                session._flags.discard("act0:key_taken")
                session._flags.remove(missing)
                session._files.show()
                session.handle_action("files_close")
                self.assertNotIn("act0:archive_closed", session._flags)
                session._flags.add(missing)

    def test_letter_does_not_require_old_card_or_assessment_and_last_line_is_separate(self):
        _, scene = self.scene()
        session = scene.session
        session._files.show()
        session.handle_action("files_year:1981")
        session.handle_action("files_case")
        session.handle_action("files_letter")
        self.assertEqual(session.dialog.presentation, "document")
        self.assertNotIn("act0:letter_read", session._flags)
        self.assertFalse(session.handle_action("document_close"))
        self.assertEqual(session._document_pages[-1], "Буду жить ради неё!")
        read_document(session)
        self.assertIn("act0:archive_reviewed", session._flags)
        self.assertNotIn("act0:archive_card_read", session._flags)
        self.assertNotIn("act0:assessment_read", session._flags)
        self.assertFalse(scene.player.inventory.has_key("second_floor_key"))
        session.handle_action("files_letter")
        self.assertEqual(session.dialog.presentation, "document")
        self.assertNotIn("матери", session.dialog.title.lower())

    def test_archive_buttons_fit_and_click_at_scaled_window_sizes(self):
        _, scene = self.scene()
        session = scene.session
        session._flags.update(("act0:map", "act0:archive_card_read"))
        overlay = DialogOverlay.__new__(DialogOverlay)
        overlay._style = create_hud_style()
        overlay._font = pygame.font.Font(str(overlay._style.font_path), 18)
        overlay._title_font = pygame.font.Font(str(overlay._style.font_path), 28)
        session._files.show()
        for action in (None, "files_year:1975", "files_back", "files_year:1981", "files_case"):
            if action:
                session.handle_action(action)
            dialog = session.dialog
            surface = pygame.Surface((640, 480), pygame.SRCALPHA)
            overlay._draw_filing_archive(surface, dialog, (640, 480), None)
            rects = dialog_button_rects(dialog, (640, 480))
            for button, rect in zip(dialog.buttons, rects):
                self.assertTrue(surface.get_rect().contains(rect))
                point = (192 + rect.centerx * 1.8, rect.centery * 1.8)
                self.assertEqual(dialog_action_at(dialog, point, (1536, 864), (640, 480)), button.action)

    def test_opening_drawer_from_modal_browser_does_not_crash_player_hud(self):
        _, scene = self.scene()
        session, player = scene.session, scene.player
        player.body = make_body(player.body.world, (9.52, 0, 3))
        drawer = self.objects(scene)[ARCHIVE_DRAWER_ID]
        eye = tuple(player.body.eye_position(settings.PLAYER_EYE_HEIGHT))
        camera = Camera(eye, drawer.current_state.selection_box.position, 65, 0.1, 100)
        player._interactions.update(0, camera)
        self.assertIs(player._interactions.focused, drawer)
        session._files.show()
        self.assertTrue(session.handle_action("files_year:1981"))
        self.assertTrue(drawer.transitioning)
        # The application reads aim_text every render, including paused modal frames.
        for _ in range(4):
            self.assertIsInstance(player.aim_text, str)
            self.assertNotIn("[E]", player.aim_text)
            drawer.update(0.05)

    def test_card_can_be_read_at_screenshot_position_with_companion_nearby_before_plan(self):
        _, scene = self.scene()
        session, player = scene.session, scene.player
        session._flags.add("act0:reception")
        self.assertNotIn("act0:map", session._flags)
        # The debug panel rounds coordinates; stay 1 cm clear of the counter.
        player.body = make_body(player.body.world, (10.53, 0, 5.58))
        ally = session.companions[0]
        ally.body._position = glm.vec3(11.9, 0, 4.8)
        ally._sync_pose()
        player._active_camera_zone = None
        player.update(0, InputState(interact=True))
        self.assertEqual(player._interactions.focused.name, "archive_card")
        self.assertIn("Архивная карточка", player.aim_text)
        session.update(0)
        self.assertEqual(session.dialog.presentation, "document")
        self.assertIn("РЕГИСТРАЦИОННАЯ КАРТОЧКА", session.dialog.message)
        read_document(session)
        self.assertIn("act0:archive_card_read", session._flags)
        self.assertTrue(player.inventory.has_item("archive_card"))
        self.assertNotIn("act0:complete", session._flags)


if __name__ == "__main__":
    unittest.main()
