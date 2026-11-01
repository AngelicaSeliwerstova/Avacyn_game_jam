import json
from dataclasses import replace
from pathlib import Path
import unittest

import pygame

from engine.rendering.dialog import DialogOverlay, dialog_action_at, dialog_button_rects
from engine.scene.session import Dialog, DialogButton
from game.ui import create_hud_style


class RecordingSurface(pygame.Surface):
    def __init__(self, size):
        super().__init__(size, pygame.SRCALPHA)
        self.text_rects = []

    def blit(self, source, dest, *args, **kwargs):
        self.text_rects.append(source.get_rect(topleft=dest))
        return super().blit(source, dest, *args, **kwargs)


class DialogueLayoutTests(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.size = (640, 480)
        self.overlay = DialogOverlay.__new__(DialogOverlay)
        self.overlay._style = create_hud_style()
        self.overlay._font = pygame.font.Font(str(self.overlay._style.font_path), 18)

    def draw(self, dialog):
        surface = RecordingSurface(self.size)
        self.overlay._draw_conversation(surface, dialog, self.size, None)
        return surface

    def assert_text_fits(self, dialog, surface):
        buttons = dialog_button_rects(dialog, self.size)
        title, *message = surface.text_rects[:-len(buttons)]
        panel = surface.get_bounding_rect()
        self.assertTrue(surface.get_rect().contains(panel))
        self.assertLessEqual(title.bottom + 6, message[0].top)
        for rect in message:
            self.assertTrue(panel.contains(rect))
            self.assertLessEqual(rect.bottom + 12, buttons[0].top)
        for rect in buttons:
            self.assertTrue(panel.contains(rect))

    def test_screenshot_reply_fits_and_panel_stays_steady_during_reveal(self):
        path = Path(__file__).resolve().parents[1] / "resources/story/hospital/acts/act0/dialogue.json"
        message = json.loads(path.read_text(encoding="utf-8"))["case_reading"][3]["text"]
        dialog = Dialog("Ответ из дела", message,
                        (DialogButton("Далее E / Enter", "next"),), presentation="conversation")
        surface = self.draw(dialog)
        self.assert_text_fits(dialog, surface)
        for count in (0, 20, len(message) // 2):
            partial = self.draw(replace(dialog, visible_characters=count))
            self.assertEqual(partial.get_bounding_rect(), surface.get_bounding_rect())

    def test_more_than_three_lines_and_four_choices_fit_without_overlap(self):
        dialog = Dialog("Собеседник", "\n".join(["Полная строка реплики"] * 6),
                        tuple(DialogButton(f"Ответ {i}", f"choice:{i}") for i in range(4)),
                        presentation="conversation")
        surface = self.draw(dialog)
        self.assertEqual(len(surface.text_rects), 1 + 6 + 4)
        self.assert_text_fits(dialog, surface)

    def test_conversation_memory_and_voiceover_buttons_click_where_drawn(self):
        for presentation in ("conversation", "memory", "voiceover"):
            dialog = Dialog("Голос", "Реплика", (DialogButton("Далее", "next"),),
                            presentation=presentation)
            surface = self.draw(dialog)
            rect, = dialog_button_rects(dialog, self.size)
            self.assertTrue(rect.contains(surface.text_rects[-1]))
            point = (192 + rect.centerx * 1.8, rect.centery * 1.8)
            self.assertEqual(dialog_action_at(dialog, point, (1536, 864), self.size), "next")
