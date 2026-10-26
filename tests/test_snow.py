from dataclasses import replace
import unittest

from config import settings
from engine.collision.aabb import AABB
from engine.particles.snow import Snowfall, SnowSettings
from game.levels import create_level


class SnowTests(unittest.TestCase):
    def setUp(self):
        self.settings = SnowSettings(60, 5.0, 0.65, 0.05, (210, 220, 235), 7)
        self.bounds = AABB(-10, -10, 10, 10)

    def make_snow(self):
        return Snowfall(self.settings, self.bounds, ())

    def test_falling_and_recycling_are_independent_of_fps(self):
        expected = self.make_snow()
        expected.update(30.0)  # Несколько полных падений, включая возврат наверх.
        for fps in (30, 60, 120):
            snow = self.make_snow()
            start = snow.positions
            for _ in range(fps * 30):
                snow.update(1 / fps)
            self.assertNotEqual(start, snow.positions)
            for actual, reference, initial in zip(snow.positions, expected.positions, start):
                self.assertEqual((actual[0], actual[2]), (initial[0], initial[2]))
                self.assertAlmostEqual(actual[1], reference[1], places=9)
                self.assertTrue(0 <= actual[1] < self.settings.height)

    def test_corridor_snow_stays_in_open_passages(self):
        level = create_level("corridor")
        obstacles = tuple(box.footprint for box in level.boxes)
        snow = Snowfall(replace(self.settings, count=settings.SNOW_COUNT), level.floor_bounds, obstacles)
        snow.update(123.5)
        self.assertEqual(len(snow.positions), settings.SNOW_COUNT)
        for x, _, z in snow.positions:
            self.assertTrue(self.bounds.min_x < x < self.bounds.max_x)
            self.assertTrue(self.bounds.min_z < z < self.bounds.max_z)
            self.assertFalse(any(box.intersects_circle(x, z, self.settings.flake_size / 2)
                                 for box in obstacles))

    def test_same_seed_and_reading_positions_keep_field_stable(self):
        snow = self.make_snow()
        initial = snow.positions
        self.assertEqual(initial, self.make_snow().positions)
        snow.update(0)
        self.assertEqual(initial, snow.positions)

    def test_empty_and_fully_blocked_areas(self):
        empty = Snowfall(replace(self.settings, count=0), self.bounds, (self.bounds,))
        empty.update(1)
        self.assertEqual(empty.positions, ())
        with self.assertRaisesRegex(ValueError, "open space"):
            Snowfall(self.settings, self.bounds, (self.bounds,))

    def test_invalid_settings_and_delta_time(self):
        for changes in ({"height": 0}, {"fall_speed": -1}, {"flake_size": float("nan")},
                        {"color": (256, 0, 0)}, {"count": -1}):
            with self.assertRaises(ValueError):
                replace(self.settings, **changes)
        snow = self.make_snow()
        before = snow.positions
        for delta in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                snow.update(delta)
        self.assertEqual(before, snow.positions)


if __name__ == "__main__":
    unittest.main()
