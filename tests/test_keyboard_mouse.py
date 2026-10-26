from collections import defaultdict
import unittest
from unittest.mock import patch

import pygame

from engine.input.bindings import InputBindings
from engine.input.keyboard_mouse import KeyboardMouse


class KeyboardMouseTests(unittest.TestCase):
    def setUp(self):
        self.keys = defaultdict(bool)
        self.grab = self.patch("pygame.event.set_grab")
        self.visible = self.patch("pygame.mouse.set_visible")
        self.motion = self.patch("pygame.mouse.get_rel", return_value=(0, 0))
        self.patch("pygame.key.get_focused", return_value=True)
        self.patch("pygame.key.get_pressed", return_value=self.keys)
        self.bindings = InputBindings(
            pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d, pygame.K_ESCAPE, 1,
        )
        self.input = KeyboardMouse(self.bindings)

    def patch(self, target, **kwargs):
        patcher = patch(target, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_opposite_keys_cancel_each_other(self):
        for key in (pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d):
            self.keys[key] = True
        self.assertEqual(self.input.read(), (0, 0, (0, 0)))

    def test_first_mouse_delta_after_capture_is_discarded(self):
        self.motion.return_value = (500, 300)
        self.assertEqual(self.input.read()[2], (0, 0))
        self.motion.return_value = (7, -2)
        self.assertEqual(self.input.read()[2], (7, -2))

    def test_escape_stops_input_until_click_and_discards_resume_delta(self):
        self.keys[pygame.K_w] = True
        self.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(self.input.read(), (0, 0, (0, 0)))
        self.grab.assert_called_with(False)
        self.visible.assert_called_with(True)
        self.input.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
        self.motion.return_value = (400, 200)
        self.assertEqual(self.input.read(), (1, 0, (0, 0)))
        self.assertEqual(self.input.read(), (1, 0, (400, 200)))

    def test_focus_gain_requires_click_before_input_resumes(self):
        self.keys[pygame.K_w] = True
        self.input.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.input.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
        self.assertEqual(self.input.read(), (0, 0, (0, 0)))
        self.input.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.assertEqual(self.input.read(), (0, 0, (0, 0)))
        self.input.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
        self.assertEqual(self.input.read(), (1, 0, (0, 0)))

    def test_click_while_already_captured_does_not_reset_mouse_delta(self):
        self.input.read()
        self.motion.return_value = (7, 4)
        self.input.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
        self.assertEqual(self.input.read()[2], (7, 4))

    def test_custom_bindings_are_used(self):
        bindings = InputBindings(
            pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB, 3,
        )
        input_device = KeyboardMouse(bindings)
        self.keys[pygame.K_UP] = True
        self.keys[pygame.K_RIGHT] = True
        self.assertEqual(input_device.read(), (1, 1, (0, 0)))
        input_device.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
        self.assertEqual(input_device.read(), (0, 0, (0, 0)))
