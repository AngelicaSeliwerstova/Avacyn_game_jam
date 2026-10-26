import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import glm

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.input.state import InputState
from engine.scene.entity import Entity
from engine.scene.model import ModelComponent
from engine.scene.transform import Transform
from game.entities.player import create_player
from game.levels import create_level


class EntityTests(unittest.TestCase):
    def setUp(self):
        self.level = create_level("stairs")
        self.world = CollisionWorld3D((box.collider for box in self.level.boxes), self.level.floor_bounds)

    def test_player_without_model_follows_physical_feet_through_jump_and_stairs(self):
        with patch.object(settings, "PLAYER_MODEL", None):
            player = create_player(self.level, self.world)
        self.assertIsInstance(player, Entity)
        self.assertIsNone(player.model.source_path)
        for frame in range(240):
            player.update(1 / 60, InputState(forward=1, jump=frame == 0))
            self.assertLess(glm.length(glm.vec3(player.transform.position) - player.body.position), 1e-6)
            self.assertGreater(player.camera.position.y, player.body.position.y)
        self.assertAlmostEqual(player.body.position.y, 1.5, places=5)
        self.assertTrue(player.body.grounded)

    def test_body_heading_follows_camera_yaw_and_ignores_pitch(self):
        player = create_player(self.level, self.world)
        player.update(0, InputState(mouse_delta=(750, 500)))
        forward = glm.vec3(player.transform.matrix * glm.vec4(0, 0, -1, 0))
        view = player.camera.target - player.camera.position
        flat_view = glm.normalize(glm.vec3(view.x, 0, view.z))
        self.assertLess(glm.length(forward - flat_view), 1e-5)
        self.assertAlmostEqual(player.transform.rotation[0], 0)
        self.assertAlmostEqual(player.transform.rotation[2], 0)
        self.assertLess(view.y, -0.5)

    def test_model_local_transform_is_composed_with_owner_transform(self):
        owner = Transform(position=(10, 0, 0), rotation=(0, 90, 0))
        model = ModelComponent(local_transform=Transform(position=(0, 0, -2), scale=(2, 2, 2)))
        origin = glm.vec3(model.world_matrix(owner) * glm.vec4(0, 0, 0, 1))
        front = glm.vec3(model.world_matrix(owner) * glm.vec4(0, 0, -1, 1))
        self.assertLess(glm.length(origin - glm.vec3(8, 0, 0)), 1e-5)
        self.assertLess(glm.length(front - glm.vec3(6, 0, 0)), 1e-5)

    def test_model_reference_uses_project_path_without_reading_file(self):
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                with patch.object(settings, "PLAYER_MODEL", "player/player.glb"), patch(
                    "pathlib.Path.open", side_effect=AssertionError("A model descriptor must not load files"),
                ):
                    player = create_player(self.level, self.world)
            finally:
                os.chdir(original)
        expected = Path(__file__).resolve().parents[1] / "resources/models/player/player.glb"
        self.assertEqual(player.model.source_path, expected)

    def test_visual_model_settings_do_not_change_physics_or_camera(self):
        normal = create_player(self.level, self.world)
        with patch.object(settings, "PLAYER_MODEL_SCALE", 0.1), patch.object(
            settings, "PLAYER_MODEL_OFFSET", (0, -2, 0),
        ):
            small = create_player(self.level, self.world)
        for frame in range(120):
            inputs = InputState(forward=1, sprint=True, jump=frame == 0)
            normal.update(1 / 60, inputs)
            small.update(1 / 60, inputs)
            self.assertEqual(normal.body.position, small.body.position)
            self.assertEqual(normal.camera.position, small.camera.position)
        self.assertNotEqual(normal.model.local_transform, small.model.local_transform)


if __name__ == "__main__":
    unittest.main()
