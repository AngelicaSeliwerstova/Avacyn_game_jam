from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import pygame

from engine.core.window import Window


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.native = SimpleNamespace(size=(1280, 960))
        self.native.set_fullscreen = Mock(side_effect=self.fullscreen)
        self.native.set_windowed = Mock()
        self.set_mode = self.patch("pygame.display.set_mode", side_effect=self.create_window)
        self.patch("pygame.display.gl_set_attribute")
        self.patch("pygame.display.set_caption")
        self.patch("pygame.display.get_window_size", side_effect=lambda: self.native.size)
        self.patch("engine.core.window.SDLWindow").from_display_module.return_value = self.native

    def patch(self, target, **kwargs):
        patcher = patch(target, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def create_window(self, size, **kwargs):
        self.native.size = size

    def fullscreen(self, desktop):
        self.native.size = (1920, 1080)

    def make_window(self, size=(1280, 960)):
        return Window(size, "gamek", (3, 3), False, minimum_size=(320, 240))

    def test_startup_size_is_at_least_internal_resolution(self):
        window = self.make_window((200, 100))
        self.assertEqual(window.size, (320, 240))

    def test_resizing_below_minimum_preserves_existing_context(self):
        window = self.make_window()
        self.native.size = (200, 100)
        window.handle_event(pygame.event.Event(pygame.WINDOWSIZECHANGED, x=200, y=100))
        self.assertEqual(window.size, (320, 240))
        self.set_mode.assert_called_once()

    def test_fullscreen_returns_to_previous_window_size_without_new_context(self):
        window = self.make_window()
        self.native.size = (1001, 777)
        window.toggle_fullscreen()
        self.assertEqual(window.size, (1920, 1080))
        self.native.set_fullscreen.assert_called_once_with(desktop=True)
        window.toggle_fullscreen()
        self.assertEqual(window.size, (1001, 777))
        self.set_mode.assert_called_once()
