import unittest

from engine.rendering.presentation import integer_viewport


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
