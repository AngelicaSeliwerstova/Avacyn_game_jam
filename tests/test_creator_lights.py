from pathlib import Path
import tempfile
import unittest

from engine.scene.lighting import LightFlicker, PointLight, SpotLight, static_point_light
from game.levels.creator_lights import load_creator_lights, save_creator_lights


class CreatorLightTests(unittest.TestCase):
    def test_creator_lamps_convert_to_static_point_lights(self):
        creator_light = SpotLight(
            position=(1.0, 2.0, 3.0),
            direction=(0.0, -1.0, 0.0),
            color=(1.0, 0.78, 0.52),
            intensity=3.5,
            radius=9.0,
            flicker=LightFlicker(interval=3.2, duration=1.0, minimum=0.08, seed=2),
        )

        static_light = static_point_light(creator_light)

        self.assertIsInstance(static_light, PointLight)
        self.assertEqual(static_light.position, creator_light.position)
        self.assertEqual(static_light.color, creator_light.color)
        self.assertEqual(static_light.intensity, creator_light.intensity)
        self.assertEqual(static_light.radius, creator_light.radius)
        self.assertEqual(static_light.flicker, creator_light.flicker)

    def test_creator_lights_round_trip_and_missing_file_is_empty(self):
        lights = (
            SpotLight(
                position=(1.0, 2.0, 3.0),
                direction=(0.0, -1.0, 0.0),
                color=(1.0, 0.78, 0.52),
                intensity=3.5,
                radius=9.0,
                inner_angle=30.0,
                outer_angle=55.0,
                flicker=LightFlicker(interval=6.0, duration=0.8, minimum=0.5, seed=1),
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "maze_lights.json"
            self.assertEqual(load_creator_lights(path), ())
            save_creator_lights(path, lights)
            self.assertEqual(load_creator_lights(path), lights)

    def test_invalid_creator_light_data_reports_path_and_index(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "maze_lights.json"
            path.write_text('{"lights": [{"position": [1, 2]}]}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid light 1"):
                load_creator_lights(path)


if __name__ == "__main__":
    unittest.main()
