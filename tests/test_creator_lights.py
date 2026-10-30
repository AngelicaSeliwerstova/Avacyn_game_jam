from pathlib import Path
import tempfile
import unittest

from engine.scene.lighting import SpotLight
from game.levels.creator_lights import load_creator_lights, save_creator_lights


class CreatorLightTests(unittest.TestCase):
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
