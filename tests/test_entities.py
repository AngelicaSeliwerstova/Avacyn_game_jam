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
from engine.scene.box import Box
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

    def test_third_person_camera_tracks_player_while_interaction_aim_stays_at_eye(self):
        player = create_player(self.level, self.world)
        player.update(0, InputState(forward=1))
        self.assertNotEqual(player.camera.position, player._interaction_camera.position)
        self.assertLess(
            glm.length(player._interaction_camera.position - player.camera.position), 5.0,
        )
        self.assertLess(
            glm.length(player._interaction_camera.position - player.camera.target), 5.0,
        )

    def test_third_person_camera_stops_before_wall_behind_player(self):
        wall = Box((0, 1.5, 7.5), (4, 3, 0.2))
        world = CollisionWorld3D(
            (*tuple(box.collider for box in self.level.boxes), wall.collider),
            self.level.floor_bounds,
        )
        player = create_player(self.level, world)
        open_player = create_player(self.level, self.world)
        wall_front = wall.collider.footprint.min_z
        self.assertGreater(open_player.camera.position.z, wall_front)
        self.assertLessEqual(
            player.camera.position.z,
            wall_front - settings.PLAYER_CAMERA_WALL_MARGIN + 1e-3,
        )
        self.assertGreater(player.camera.position.z, player.body.position.z)

    def test_look_back_turns_camera_without_turning_character_and_stops_at_wall(self):
        wall = Box((0, 1.5, 4.5), (4, 3, 0.2))
        world = CollisionWorld3D(
            (*tuple(box.collider for box in self.level.boxes), wall.collider),
            self.level.floor_bounds,
        )
        player = create_player(self.level, world)
        heading = glm.vec3(player.transform.matrix * glm.vec4(0, 0, -1, 0))
        normal_camera = glm.vec3(player.camera.position)
        player.update(0, InputState(look_back=True))
        view = glm.normalize(glm.vec3(player.camera.target - player.camera.position) * glm.vec3(1, 0, 1))
        interaction = glm.normalize(glm.vec3(player._interaction_camera.target - player._interaction_camera.position)
                                    * glm.vec3(1, 0, 1))
        self.assertLess(glm.dot(heading, view), -0.99)
        self.assertLess(glm.dot(heading, interaction), -0.99)
        self.assertEqual(glm.vec3(player.transform.matrix * glm.vec4(0, 0, -1, 0)), heading)
        self.assertLess(player.camera.position.z, player.body.position.z)
        self.assertGreaterEqual(player.camera.position.z, wall.collider.footprint.max_z + 0.19)
        player.update(0, InputState())
        self.assertLess(glm.length(player.camera.position - normal_camera), 1e-5)

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
