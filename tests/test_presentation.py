import unittest
from unittest.mock import Mock

from engine.rendering.hud import CreatorSidebarOverlay
from engine.rendering.presentation import horizontal_side_bars, integer_viewport


class PresentationTests(unittest.TestCase):
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
        self.assertEqual(horizontal_side_bars((1920, 1080), (640, 480)), (320, 320))
        self.assertEqual(horizontal_side_bars((1280, 960), (640, 480)), (0, 0))
        self.assertEqual(horizontal_side_bars((600, 900), (320, 240)), (140, 140))

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
