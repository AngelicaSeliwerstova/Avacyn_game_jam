import json
from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from config import settings
from engine.input.state import InputState
from engine.scene.box import Box
from engine.scene.camera import FixedCameraZone
from game.campaign import Campaign
from game.levels import create_level
from game.levels.cameras import save_fixed_cameras
from game.levels.creator import save_creator_objects
from game.levels.location import load_location


class LocationTests(unittest.TestCase):
    def test_start_is_clear_and_has_no_old_objectives(self):
        campaign = Campaign()
        # Test the authored start, independently of the developer's saved layout.
        with patch("game.levels.location.load_creator_objects", return_value=()), \
                patch("game.levels.location.load_removed_objects", side_effect=lambda path: set()):
            scene = campaign.load_level(settings.LEVEL_NAME)
        self.assertEqual(settings.LEVEL_NAME, "peaceful")
        self.assertTrue(scene.level.objects)
        self.assertEqual(scene.level.creator_objects, ())
        self.assertEqual(len(scene.session.goals), 0)
        self.assertFalse(scene.player.body.world.is_blocked(
            scene.player.body.position, scene.player.body.radius, scene.player.body.height))
        scene.player.update(1 / 60, InputState())
        scene.session.update(1 / 60)
        self.assertIn("Найти свой кабинет", scene.player.objective_status)
        self.assertIsNone(scene.session.next_level)

    def test_retired_levels_are_unavailable(self):
        for name in ("maze", "corridor", "stairs", "demo", "../start", "", "/start"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                create_level(name)

    def test_start_loads_from_other_working_directory(self):
        expected = create_level("start")
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                actual = create_level("start")
                self.assertEqual(replace(actual, objects=(), navigation=None),
                                 replace(expected, objects=(), navigation=None))
                self.assertEqual(actual.navigation.points, expected.navigation.points)
                self.assertEqual([(obj.name, dict(obj.states)) for obj in actual.objects],
                                 [(obj.name, dict(obj.states)) for obj in expected.objects])
            finally:
                os.chdir(original)

    def test_creator_data_is_separate_for_each_location(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = {"floor_size": [20, 20], "spawn_position": [0, 1.6, 0],
                    "spawn_target": [0, 1.6, -1]}
            for name in ("first", "second"):
                (root / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
            camera = FixedCameraZone((-1, -1, -1), (1, 3, 1), (0, 2, 0), (0, 2, -4))
            box = Box((3, 1, 0), (1, 2, 1), material="concrete")
            save_fixed_cameras(root / "first_cameras.json", (camera,))
            save_creator_objects(root / "first_objects.json", (box,))
            first = load_location(root / "first.json")
            second = load_location(root / "second.json")
            self.assertEqual(first.fixed_cameras, (camera,))
            self.assertEqual(first.creator_objects, (box,))
            self.assertEqual(second.fixed_cameras, ())
            self.assertEqual(second.creator_objects, ())
            self.assertNotEqual(first.creator_lights_path, second.creator_lights_path)
            with patch("game.levels.LEVELS_ROOT", root):
                scene = Campaign(creator_mode=True).load_level("first")
                self.assertTrue(scene.player.creator_mode)

    def test_location_keeps_doors_keys_lights_and_transitions_available(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "new.json"
            path.write_text(json.dumps({
                "floor_size": [20, 20], "spawn_position": [0, 1.6, 0],
                "spawn_target": [0, 1.6, -1],
                "lighting": {"lights": [{"position": [0, 3, 0], "flicker": {"seed": 3}}]},
                "objects": [
                    {"id": "key", "type": "key", "key_id": "story", "position": [3, 0, 3]},
                    {"id": "door", "type": "door", "key_id": "story", "position": [0, 0, -3]},
                    {"id": "exit", "type": "exit", "position": [0, 0, -6], "next_level": "second"},
                ],
            }), encoding="utf-8")
            level = load_location(path)
            self.assertEqual(level.lighting.lights[0].flicker.seed, 3)
            objects = {obj.name: obj for obj in level.objects}
            self.assertEqual(objects["door"].interaction.command, "unlock_door")
            self.assertEqual(objects["key"].interaction.command, "pickup_key")
            self.assertEqual(objects["exit"].entity.next_level, "second")


if __name__ == "__main__":
    unittest.main()
