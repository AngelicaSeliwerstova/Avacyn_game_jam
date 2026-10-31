import unittest
from unittest.mock import Mock

from engine.rendering.hud import CreatorSidebarOverlay
from engine.rendering.presentation import horizontal_side_bars, integer_viewport, fit_viewport
from engine.rendering.dialog import dialog_action_at, button_rects
from engine.scene.session import Dialog, DialogButton


class PresentationTests(unittest.TestCase):
    def test_fitted_view_uses_full_height_at_reported_window_size(self):
        self.assertEqual(fit_viewport((1536, 864), (640, 480)), (192, 0, 1152, 864))
        self.assertEqual(fit_viewport((1920, 1080), (640, 480)), (240, 0, 1440, 1080))
        self.assertEqual(fit_viewport((1280, 960), (640, 480)), (0, 0, 1280, 960))
        self.assertEqual(fit_viewport((600, 900), (640, 480)), (0, 225, 600, 450))

    def test_fitted_view_keeps_aspect_ratio_and_fills_one_dimension(self):
        for width in range(100, 2200, 137):
            for height in range(100, 1600, 109):
                x, y, w, h = fit_viewport((width, height), (640, 480))
                self.assertTrue(w == width or h == height)
                self.assertLessEqual(w, width)
                self.assertLessEqual(h, height)
                self.assertLess(abs(w * 480 - h * 640), 640)
                self.assertLessEqual(abs(x - (width - x - w)), 1)
                self.assertLessEqual(abs(y - (height - y - h)), 1)
        self.assertEqual(fit_viewport((0, 0), (640, 480)), (0, 0, 0, 0))

    def test_dialog_mouse_hits_follow_fractional_scaling(self):
        dialog = Dialog("End", "", (DialogButton("Restart", "restart"),))
        rect = button_rects((640, 480), 1)[0]
        point = (192 + rect.centerx * 1.8, rect.centery * 1.8)
        self.assertEqual(dialog_action_at(dialog, point, (1536, 864), (640, 480)), "restart")
        self.assertIsNone(dialog_action_at(dialog, (10, 400), (1536, 864), (640, 480)))

    def test_known_window_sizes(self):
        for window, expected in (
            ((1280, 960), (0, 0, 1280, 960)),
            ((1920, 1080), (320, 60, 1280, 960)),
            ((1001, 777), (20, 28, 960, 720)),
            ((600, 900), (140, 330, 320, 240)),
            ((320, 240), (0, 0, 320, 240)),
        ):
            with self.subTest(window=window):
                self.assertEqual(integer_viewport(window, (320, 240)), expected)

    def test_many_sizes_keep_square_pixels_and_centered_image(self):
        for width in range(320, 2200, 137):
            for height in range(240, 1600, 109):
                x, y, scaled_width, scaled_height = integer_viewport((width, height), (320, 240))
                self.assertEqual(scaled_width % 320, 0)
                self.assertEqual(scaled_width // 320, scaled_height // 240)
                self.assertLessEqual(x + scaled_width, width)
                self.assertLessEqual(y + scaled_height, height)
                self.assertLessEqual(abs(x - (width - x - scaled_width)), 1)
                self.assertLessEqual(abs(y - (height - y - scaled_height)), 1)
                scale = scaled_width // 320
                self.assertTrue((scale + 1) * 320 > width or (scale + 1) * 240 > height)

    def test_temporary_tiny_or_minimized_window_has_no_partial_image(self):
        for size in ((0, 0), (319, 240), (320, 239)):
            with self.subTest(size=size):
                self.assertEqual(integer_viewport(size, (320, 240)), (0, 0, 0, 0))

    def test_horizontal_letterbox_bars_are_available_for_creator_controls(self):
        self.assertEqual(horizontal_side_bars((1920, 1080), (640, 480)), (240, 240))
        self.assertEqual(horizontal_side_bars((1280, 960), (640, 480)), (0, 0))
        self.assertEqual(horizontal_side_bars((600, 900), (320, 240)), (0, 0))

    def test_creator_controls_fall_back_inside_the_game_view_when_sidebars_are_missing(self):
        overlay = CreatorSidebarOverlay.__new__(CreatorSidebarOverlay)
        overlay._margin = 8
        overlay._left = Mock()
        overlay._right = Mock()

        overlay.draw((1280, 960), (640, 480), ("CREATOR", "SCENE"))

        overlay._left.draw.assert_called_once_with(
            "CREATOR", (1280, 960), anchor="center_left", max_width=180,
            fill_width=True, anchor_bounds=(0, 0, 1280, 960),
        )
        overlay._right.draw.assert_called_once_with(
            "SCENE", (1280, 960), anchor="center_right", max_width=180,
            fill_width=True, anchor_bounds=(0, 0, 1280, 960),
        )
