from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from engine.scene.lighting import Lighting, PointLight
from game.levels.maze import create_maze_level, maze_layout_path
from game.levels.maze_layout import load_maze_layout


class LightingTests(unittest.TestCase):
    def test_invalid_parameters_are_rejected(self):
        light = PointLight((0, 3, 0))
        for values in ({"radius": 0}, {"intensity": -1}, {"position": (0, float("nan"), 0)},
                       {"color": (1, -1, 0)}, {"radius": float("inf")}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                replace(light, **values)
        for values in ({"ambient": (-1, 0, 0)}, {"lights": (light,) * 129}, {"shadow_resolution": 0}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                replace(Lighting((0.2, 0.2, 0.2), (light,)), **values)

    def test_authored_lamps_have_clear_positions_and_do_not_change_collision_geometry(self):
        layout = load_maze_layout(maze_layout_path())
        level = create_maze_level()
        self.assertEqual(level.lighting, layout.lighting)
        self.assertEqual(len(level.boxes), 355)
        self.assertTrue(any(any(box.emission) for box in level.decorations))
        for light in level.lighting.lights:
            for box in level.boxes:
                self.assertFalse(all(abs(p - c) < size / 2
                                     for p, c, size in zip(light.position, box.position, box.size)), light)

    def test_edited_lamp_in_wall_is_rejected_and_old_maps_remain_valid(self):
        data = json.loads(maze_layout_path().read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "maze.json"
            data["lighting"]["lamps"][0]["node"] = [0, 0, 0]
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_maze_layout(path)
            del data["lighting"]
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertIsNone(load_maze_layout(path).lighting)


if __name__ == "__main__":
    unittest.main()
