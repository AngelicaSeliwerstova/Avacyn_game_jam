from dataclasses import replace
import unittest
from unittest.mock import patch

from config import settings
from game.effects import create_postprocess_settings


class PostProcessTests(unittest.TestCase):
    def test_effect_can_be_disabled(self):
        with patch.object(settings, "POSTPROCESS_ENABLED", False):
            self.assertIsNone(create_postprocess_settings())

    def test_effect_parameters_reject_nonfinite_or_invalid_values(self):
        style = create_postprocess_settings()
        for change in ({"strength": -1}, {"saturation": 2}, {"bloom_threshold": float("nan")},
                       {"bloom_strength": -1}, {"bloom_radius": 0}, {"downsample": 3},
                       {"tint": (1, float("inf"), 1)}, {"bloom_color": (-1, 0, 0)}):
            with self.assertRaises(ValueError):
                replace(style, **change)

    def test_tint_and_glow_can_be_tuned_independently(self):
        with patch.object(settings, "COLD_STRENGTH", 0), patch.object(settings, "BLOOM_STRENGTH", 0.8):
            glow = create_postprocess_settings()
        self.assertEqual(glow.strength, 0)
        self.assertEqual(glow.bloom_strength, 0.8)
        with patch.object(settings, "COLD_STRENGTH", 0.6), patch.object(settings, "BLOOM_STRENGTH", 0):
            tint = create_postprocess_settings()
        self.assertEqual(tint.strength, 0.6)
        self.assertEqual(tint.bloom_strength, 0)


if __name__ == "__main__":
    unittest.main()
