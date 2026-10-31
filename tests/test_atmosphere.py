from dataclasses import replace
import unittest
from unittest.mock import patch

from config import settings
from engine.rendering.fog import FogSettings
from engine.scene.box import Box
from engine.scene.level import Level
from engine.scene.lighting import LightFlicker, Lighting, PointLight
from game.effects import create_fog_settings


class AtmosphereTests(unittest.TestCase):
    def test_fog_settings_and_independent_disable(self):
        self.assertIsInstance(create_fog_settings(), FogSettings)
        with patch.object(settings, "FOG_ENABLED", False):
            self.assertIsNone(create_fog_settings())
        for values in ({"start": -1}, {"start": 30}, {"end": float("inf")},
                       {"start": float("nan")}, {"color": (1, 2, 0)}, {"color": (0, 0)}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                replace(FogSettings(), **values)

    def test_flicker_is_rare_bounded_and_has_a_real_dip(self):
        flicker = LightFlicker()
        samples = [flicker.brightness(index / 600) for index in range(4800)]
        self.assertTrue(all(flicker.minimum <= value <= 1 for value in samples))
        self.assertAlmostEqual(min(samples), flicker.minimum, delta=0.001)
        self.assertGreater(samples.count(1.0) / len(samples), 0.9)
        self.assertEqual(samples, [flicker.brightness(index / 600) for index in range(4800)])

    def test_animation_time_is_independent_of_frame_rate(self):
        flicker = LightFlicker(seed=19)
        samples = []
        for fps in (30, 60, 120):
            elapsed, values = 0.0, []
            for frame in range(12 * fps):
                elapsed += 1 / fps
                if (frame + 1) % (fps // 30) == 0:
                    values.append(flicker.brightness(elapsed))
            samples.append(values)
        for values in samples[1:]:
            for actual, expected in zip(values, samples[0]):
                self.assertAlmostEqual(actual, expected, places=10)

    def test_seed_desynchronizes_lamps_and_invalid_parameters_are_rejected(self):
        a, b = LightFlicker(seed=1), LightFlicker(seed=2)
        self.assertNotEqual([a.brightness(i / 30) for i in range(240)],
                            [b.brightness(i / 30) for i in range(240)])
        for values in ({"duration": 0}, {"duration": 8}, {"interval": float("inf")},
                       {"minimum": -1}, {"minimum": float("nan")}, {"seed": 0.5}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                replace(a, **values)
        for elapsed in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                a.brightness(elapsed)

    def test_invalid_panel_links_are_rejected(self):
        with self.assertRaises(ValueError):
            Box((0, 1, 0), (1, 1, 1), emission_light=-1)
        panel = Box((0, 1, 0), (1, 1, 1), emission_light=1)
        with self.assertRaises(ValueError):
            Level((10, 10), 1, (), (0, 1.6, 4), (0, 1.6, 0), ((80, 80, 80),) * 2,
                  decorations=(panel,), lighting=Lighting((0.1, 0.1, 0.1), (PointLight((0, 3, 0)),)))
