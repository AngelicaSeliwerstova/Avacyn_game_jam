import unittest
from unittest.mock import patch

import glm
import pygame

from config import settings
from engine.input.state import InputState
from engine.rendering.dialog import DialogOverlay, dialog_action_at, dialog_button_rects
from game.campaign import Campaign
from game.story import StorySession
from game.ui import create_hud_style
from support_story import finish_conversation
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
        self.assertIsNone(session.dialog)
        session.actors["doctor"].request_talk()
        session.update(0)
        self.assertEqual(session.dialog.message, session.act.dialogues["meeting"][0]["text"])
        finish_conversation(session, choice)
        self.assertEqual(session.dialog.presentation, "interference")
        self.assertIsNone(session.next_level)
        session.tick_presentation(3.6)
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

    def test_all_three_responses_converge_without_skipping_required_reading(self):
        for choice in range(3):
            with self.subTest(choice=choice):
                campaign, scene = self.enter_ruined_hospital(choice)
                session = scene.session
                self.assertFalse(session.handle_gameplay_key("m"))
                self.request_document(scene, "mother_letter")
                self.assertIsNone(session.dialog)
                self.assertNotIn("act0:letter_read", campaign.progress.flags)
                self.request_document(scene, "hospital_plan")
                self.assertFalse(session.handle_action("map_close"))
                session.handle_action("map_next")
                session.handle_action("map_next")
                self.assertTrue(session.handle_action("map_close"))
                finish_conversation(session)
                self.assertEqual(session.dialog.presentation, "document")
                self.assertFalse(session.handle_action("document_close"))
                session.handle_action("document_next")
                self.assertFalse(session.handle_action("document_close"))
                session.handle_action("document_next")
                self.assertNotIn("act0:complete", campaign.progress.flags)
                session.handle_action("document_close")
                self.assertNotIn("act0:complete", campaign.progress.flags)
                finish_conversation(session, choice)
                self.assertIn("act0:complete", campaign.progress.flags)
                for name in ("doctor", "room313", "letter"):
                    self.assertIn(f"act0:choice:{name}:{choice}", campaign.progress.flags)
                self.assertIn("Найти палату 313", scene.player.objective_status)
                self.assertTrue(session.handle_gameplay_key("m"))
                self.assertTrue(session.handle_action("map_close"))
                self.assertIsNone(session.dialog)
                self.assertEqual(len(scene.player.inventory.items), 2)
                self.request_document(scene, "mother_letter")
                session.handle_action("document_close")
                self.assertIsNone(session.dialog)
                self.assertEqual(len(scene.player.inventory.items), 2)

    def test_office_door_documents_and_reception_are_physically_reachable(self):
        campaign = Campaign()
        scene = campaign.load_level("peaceful")
        session = scene.session
        session.tick_presentation(4)
        door = next(obj for obj in scene.level.objects if obj.name == "office_0")
        door.set_state("open")
        door.update(1)
        walk(self, scene.player.body, ((3.5, 0, 12.2), (3.5, 0, -4.5), (-17, 0, -4.5), (-17, 0, -8.4)))
        session.update(0)
        self.assertEqual(session.dialog.presentation, "conversation")
        finish_conversation(session)
        session.tick_presentation(4)
        scene = campaign.load_level("start")
        session = scene.session
        self.assertEqual(next(o for o in scene.level.objects if o.name == "office_0").state_name, "open")
        session.update(0)
        finish_conversation(session)
        walk(self, scene.player.body, ((-17, 0, -4.5), (3.5, 0, -4.5), (3.5, 0, 9.5),
                                      (19.4, 0, 9.5), (19.4, 0, 2.6), (13.4, 0, 2.3)))
        session.update(0)
        self.assertIn("act0:reception", campaign.progress.flags)
        finish_conversation(session)
        scene.player.update(0, InputState(interact=True))
        self.assertEqual(scene.player._interactions.focused.name, "hospital_plan")
        session.update(0)
        session.handle_action("map_next")
        session.handle_action("map_next")
        session.handle_action("map_close")
        finish_conversation(session)
        session.handle_action("document_next")
        session.handle_action("document_next")
        session.handle_action("document_close")
        finish_conversation(session)
        walk(self, scene.player.body, ((19.4, 0, 2.6), (19.4, 0, 9.5), (12, 0, 9.5)))
        session.update(0)
        self.assertIn("act0:ending", campaign.progress.flags)
        finish_conversation(session)
        self.assertTrue(session.actors["doctor"].following)
        self.assertEqual(session.act.id, "act1")
        self.assertEqual(session.dialog.presentation, "title")
        session.tick_presentation(4)
        finish_conversation(session)
        self.assertIsNone(session.dialog)
        # Letter is reachable from the public side of the registration counter.
        walk(self, scene.player.body, ((11.6, 0, 7.4),))
        scene.player.update(0, InputState(interact=True))
        self.assertEqual(scene.player._interactions.focused.name, "mother_letter")

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
