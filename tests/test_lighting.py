from dataclasses import replace
import unittest

from engine.scene.lighting import Lighting, PointLight, MAX_POINT_LIGHTS


class LightingTests(unittest.TestCase):
    def test_invalid_parameters_are_rejected(self):
        light = PointLight((0, 3, 0))
        for values in ({"radius": 0}, {"intensity": -1}, {"position": (0, float("nan"), 0)},
                       {"color": (1, -1, 0)}, {"radius": float("inf")}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                replace(light, **values)
        for values in ({"ambient": (-1, 0, 0)}, {"lights": (light,) * (MAX_POINT_LIGHTS + 1)}, {"shadow_resolution": 0}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                replace(Lighting((0.2, 0.2, 0.2), (light,)), **values)


if __name__ == "__main__":
    unittest.main()
