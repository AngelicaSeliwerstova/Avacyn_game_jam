import unittest

import pygame

from engine.rendering.dialog import DialogOverlay, conversation_rects, dialog_action_at
from engine.rendering.hud import HudStyle
from game.campaign import Campaign
from game.dialogue import validate_dialogue


class DialogueChoiceTests(unittest.TestCase):
    def start_conversation(self):
        scene = Campaign().load_level("peaceful")
        ally = scene.session.companions[0]
        ally.talk_requested = True
        scene.session.update(0)
        return scene, ally

    def test_answers_branch_and_only_explicit_agreement_recruits(self):
        scene, ally = self.start_conversation()
        session = scene.session
        self.assertEqual(len(session.dialog.buttons), 2)
        self.assertFalse(session.handle_action("dialogue_next"))
        first_text = session.dialog.message
        session.handle_action("dialogue_choice:1")
        self.assertNotEqual(session.dialog.message, first_text)
        session.handle_action("dialogue_choice:1")
        self.assertIsNone(session.dialog)
        self.assertIsNone(session.next_level)
        self.assertFalse(ally.following)
        ally.talk_requested = True
        session.update(0)
        for _ in range(3):
            session.handle_action("dialogue_choice:0")
        self.assertTrue(ally.following)
        self.assertEqual(session.next_level, "start")
        self.assertIn("asked_about_noise", session._flags)
        self.assertIn("recruited:hospital_companion", session._flags)

    def test_unknown_choices_and_invalid_graphs_are_rejected(self):
        scene, _ = self.start_conversation()
        original = scene.session.dialog
        self.assertFalse(scene.session.handle_action("dialogue_choice:99"))
        self.assertEqual(scene.session.dialog, original)
        for nodes in (({"text": "Hello", "choices": []},),
                      ({"text": "Hello", "choices": [{"label": "Go", "next": 4}]},),
                      ({"text": "Hello", "choices": [{"label": "Go"}]},)):
            with self.assertRaises(ValueError):
                validate_dialogue(nodes)
        self.assertEqual(validate_dialogue(("Hello", "Goodbye")), ("Hello", "Goodbye"))

    def test_conversation_panel_leaves_world_transparent_and_buttons_click_at_scaled_sizes(self):
        pygame.font.init()
        scene, _ = self.start_conversation()
        dialog = scene.session.dialog
        overlay = DialogOverlay.__new__(DialogOverlay)
        overlay._style = HudStyle()
        overlay._font = pygame.font.Font(None, 18)
        surface = pygame.Surface((640, 480), pygame.SRCALPHA)
        overlay._draw_conversation(surface, dialog, (640, 480), None)
        self.assertEqual(surface.get_at((320, 100)).a, 0)
        panel, buttons = conversation_rects((640, 480), len(dialog.buttons))
        self.assertGreater(surface.get_at(panel.center).a, 0)
        for index, rect in enumerate(buttons):
            point = (192 + rect.centerx * 1.8, rect.centery * 1.8)
            self.assertEqual(dialog_action_at(dialog, point, (1536, 864), (640, 480)), f"dialogue_choice:{index}")
        self.assertIsNone(dialog_action_at(dialog, (768, 100), (1536, 864), (640, 480)))
