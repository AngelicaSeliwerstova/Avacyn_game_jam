from collections import defaultdict
import unittest
from unittest.mock import patch

import pygame

from engine.input.bindings import InputBindings
from engine.input.keyboard_mouse import KeyboardMouse
from engine.input.state import InputState


class KeyboardMouseTests(unittest.TestCase):
    def setUp(self):
        self.keys = defaultdict(bool)
        self.grab = self.patch("pygame.event.set_grab")
        self.visible = self.patch("pygame.mouse.set_visible")
        self.motion = self.patch("pygame.mouse.get_rel", return_value=(0, 0))
        self.buttons = [False] * 5
        self.patch("pygame.mouse.get_pressed", side_effect=lambda count: tuple(self.buttons))
        self.patch("pygame.key.get_focused", return_value=True)
        self.patch("pygame.key.get_pressed", return_value=self.keys)
        self.bindings = InputBindings(
            pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d, pygame.K_ESCAPE, 1,
            sprint_keys=(pygame.K_LSHIFT, pygame.K_RSHIFT), jump=pygame.K_SPACE,
            crouch_keys=(pygame.K_LCTRL, pygame.K_RCTRL),
            interact=pygame.K_e,
            zoom_mouse_button=3,
            look_back=pygame.K_q,
        )
        self.input = KeyboardMouse(self.bindings)

    def patch(self, target, **kwargs):
        patcher = patch(target, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_opposite_keys_cancel_each_other(self):
        for key in (pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d):
            self.keys[key] = True
        self.assertEqual(self.input.read(), InputState())

    def test_first_mouse_delta_after_capture_is_discarded(self):
        self.motion.return_value = (500, 300)
        self.assertEqual(self.input.read().mouse_delta, (0, 0))
        self.motion.return_value = (7, -2)
        self.assertEqual(self.input.read().mouse_delta, (7, -2))

    def test_escape_stops_input_until_click_and_discards_resume_delta(self):
        self.keys[pygame.K_w] = True
        self.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(self.input.read(), InputState())
        self.grab.assert_called_with(False)
        self.visible.assert_called_with(True)
        self.input.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
        self.motion.return_value = (400, 200)
        self.assertEqual(self.input.read(), InputState(1, 0, (0, 0)))
        self.assertEqual(self.input.read(), InputState(1, 0, (400, 200)))

    def test_focus_gain_requires_click_before_input_resumes(self):
        self.keys[pygame.K_w] = True
        self.input.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.input.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
        self.assertEqual(self.input.read(), InputState())
        self.input.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.assertEqual(self.input.read(), InputState())
        self.input.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
        self.assertEqual(self.input.read(), InputState(1, 0, (0, 0)))

    def test_click_while_already_captured_does_not_reset_mouse_delta(self):
        self.input.read()
        self.motion.return_value = (7, 4)
        self.input.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
        self.assertEqual(self.input.read().mouse_delta, (7, 4))

    def test_custom_bindings_are_used(self):
        bindings = InputBindings(
            pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB, 3,
        )
        input_device = KeyboardMouse(bindings)
        self.keys[pygame.K_UP] = True
        self.keys[pygame.K_RIGHT] = True
        self.assertEqual(input_device.read(), InputState(1, 1, (0, 0)))
        input_device.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
        self.assertEqual(input_device.read(), InputState())

    def test_either_shift_sprints_only_while_held(self):
        for key in self.bindings.sprint_keys:
            self.keys[key] = True
            self.assertTrue(self.input.read().sprint)
            self.keys[key] = False
            self.assertFalse(self.input.read().sprint)

    def test_q_looks_back_only_while_held_and_captured(self):
        self.keys[pygame.K_q] = True
        self.assertTrue(self.input.read().look_back)
        self.assertTrue(self.input.read().look_back)
        self.keys[pygame.K_q] = False
        self.assertFalse(self.input.read().look_back)
        self.keys[pygame.K_q] = True
        self.input.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertFalse(self.input.read().look_back)

    def test_jump_is_a_single_press_even_with_key_repeat(self):
        self.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.input.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE))
        self.assertTrue(self.input.read().jump)  # Короткое нажатие между кадрами не теряется.
        self.assertFalse(self.input.read().jump)
        self.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertTrue(self.input.read().jump)
        for repeat in (False, True):
            self.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, repeat=repeat))
            self.assertFalse(self.input.read().jump)

    def test_either_control_crouches_while_held_and_focus_loss_disables_it(self):
        for key in self.bindings.crouch_keys:
            self.keys[key] = True
            self.assertTrue(self.input.read().crouch)
            self.assertTrue(self.input.read().crouch)
            self.keys[key] = False
            self.assertFalse(self.input.read().crouch)
        self.keys[pygame.K_LCTRL] = True
        self.input.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertEqual(self.input.read(), InputState())

    def test_crouch_uses_custom_binding(self):
        bindings = InputBindings(pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d,
                                 pygame.K_ESCAPE, 1, crouch_keys=(pygame.K_c,))
        device = KeyboardMouse(bindings)
        self.keys[pygame.K_LCTRL] = True
        self.assertFalse(device.read().crouch)
        self.keys[pygame.K_c] = True
        self.assertTrue(device.read().crouch)

    def test_interact_uses_single_press_and_ignores_repeat(self):
        self.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        self.input.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_e))
        self.assertTrue(self.input.read().interact)
        self.assertFalse(self.input.read().interact)
        self.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        self.assertTrue(self.input.read().interact)
        for repeat in (False, True):
            self.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=repeat))
            self.assertFalse(self.input.read().interact)

    def test_focus_loss_and_recapture_do_not_trigger_held_interaction(self):
        self.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        self.input.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertEqual(self.input.read(), InputState())
        self.keys[pygame.K_e] = True
        self.input.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.input.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
        self.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        self.assertFalse(self.input.read().interact)
        self.input.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_e))
        self.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        self.assertTrue(self.input.read().interact)
        self.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(self.input.read(), InputState())

    def test_interaction_uses_custom_binding(self):
        bindings = InputBindings(pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d,
                                 pygame.K_ESCAPE, 1, interact=pygame.K_f)
        device = KeyboardMouse(bindings)
        device.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        self.assertFalse(device.read().interact)
        device.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f))
        self.assertTrue(device.read().interact)

    def test_zoom_is_held_right_mouse_button_and_release_stops_it(self):
        self.buttons[0] = True
        self.assertFalse(self.input.read().zoom)
        self.buttons[2] = True
        self.assertTrue(self.input.read().zoom)
        self.assertTrue(self.input.read().zoom)
        self.buttons[2] = False
        self.assertFalse(self.input.read().zoom)

    def test_escape_and_focus_loss_disable_zoom_until_recapture(self):
        self.buttons[2] = True
        for event in (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE),
                      pygame.event.Event(pygame.WINDOWFOCUSLOST)):
            self.input.handle_event(event)
            self.assertFalse(self.input.read().zoom)
            self.input.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
            self.assertFalse(self.input.read().zoom)
            self.input.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
            self.assertTrue(self.input.read().zoom)

    def test_zoom_uses_configured_mouse_button(self):
        bindings = InputBindings(pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d,
                                 pygame.K_ESCAPE, 1, zoom_mouse_button=2)
        device = KeyboardMouse(bindings)
        self.buttons[2] = True
        self.assertFalse(device.read().zoom)
        self.buttons[1] = True
        self.assertTrue(device.read().zoom)
        for button in (0, 6):
            with self.assertRaises(ValueError):
                InputBindings(pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d,
                              pygame.K_ESCAPE, 1, zoom_mouse_button=button)

    def test_release_and_focus_loss_clear_jump_and_sprint(self):
        self.keys[pygame.K_LSHIFT] = True
        self.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.input.release()
        self.assertEqual(self.input.read(), InputState())
        self.keys[pygame.K_SPACE] = True
        self.input.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
        self.assertFalse(self.input.read().jump)
        self.input.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertFalse(self.input.read().jump)
        self.input.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertEqual(self.input.read(), InputState())

    def test_jump_and_sprint_use_custom_bindings(self):
        bindings = InputBindings(pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d,
                                 pygame.K_ESCAPE, 1, sprint_keys=(pygame.K_r,), jump=pygame.K_j)
        device = KeyboardMouse(bindings)
        self.keys[pygame.K_r] = True
        device.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertFalse(device.read().jump)
        device.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j))
        self.assertEqual(device.read(), InputState(sprint=True, jump=True))
