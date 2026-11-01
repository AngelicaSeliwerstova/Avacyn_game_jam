import math
import unittest
from unittest.mock import patch

import glm

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.input.state import InputState
from engine.scene.box import Box
from engine.scene.camera import FixedCameraZone
from engine.scene.level import Level
from game.entities.player import create_player


def make_player(boxes=()):
    zone = FixedCameraZone((-10, -1, -10), (10, 3, 10), (4, 3, 4), (0, 1, 0))
    level = Level((30, 30), 1, boxes, (0, settings.PLAYER_EYE_HEIGHT, 0),
                  (0, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
                  fixed_cameras=(zone,), authored_fixed_cameras=(zone,), fixed_cameras_authored=True)
    return create_player(level, CollisionWorld3D((b.collider for b in boxes), level.floor_bounds))


class TankControlTests(unittest.TestCase):
    def test_left_and_right_rotate_body_and_flashlight_without_strafing(self):
        for axis in (-1, 1):
            player = make_player()
            position, yaw = glm.vec3(player.body.position), player.controller.yaw_degrees
            rotation = player.transform.rotation
            player.update(.1, InputState(right=axis))
            self.assertLess(glm.distance(player.body.position, position), 1e-6)
            turned = (player.controller.yaw_degrees - yaw + 180) % 360 - 180
            self.assertAlmostEqual(turned, axis * settings.PLAYER_TURN_SPEED_DEGREES * .1)
            self.assertNotEqual(player.transform.rotation, rotation)
            direction = glm.normalize(player._interaction_camera.target - player._interaction_camera.position)
            self.assertAlmostEqual(direction.x, math.cos(math.radians(player.controller.yaw_degrees)), places=5)

    def test_backing_up_does_not_turn_model_or_flashlight_around(self):
        player = make_player()
        rotation, yaw = player.transform.rotation, player.controller.yaw_degrees
        player.update(.1, InputState(forward=-1))
        self.assertGreater(player.body.position.z, 0)
        self.assertAlmostEqual(player.body.position.x, 0, places=5)
        self.assertEqual(player.transform.rotation, rotation)
        self.assertEqual(player.controller.yaw_degrees, yaw % 360)
        self.assertLess(player._interaction_camera.target.z, player._interaction_camera.position.z)

    def test_turn_then_walk_and_mouse_movement_keeps_body_heading(self):
        player = make_player()
        for _ in range(5):
            player.update(.1, InputState(right=1))
        player.update(.1, InputState(forward=1, mouse_delta=(900, -600)))
        self.assertGreater(player.body.position.x, 0)
        self.assertAlmostEqual(player.body.position.z, 0, places=5)
        self.assertAlmostEqual(player.controller.yaw_degrees, 0, places=5)
        self.assertAlmostEqual(player.controller.pitch_degrees, 0, places=5)

    def test_steering_while_walking_has_same_speed_and_turn_rate_at_different_fps(self):
        for fps in (30, 60, 120):
            player = make_player()
            distance = 0
            for _ in range(fps // 2):
                previous = glm.vec3(player.body.position)
                player.update(1 / fps, InputState(forward=1, right=1))
                distance += glm.distance(previous, player.body.position)
            self.assertAlmostEqual((player.controller.yaw_degrees + 180) % 360 - 180, 0, places=4)
            self.assertAlmostEqual(distance, settings.MOVE_SPEED * .5, places=4)
            self.assertGreater(player.body.position.x, 0)
            self.assertLess(player.body.position.z, 0)

    def test_body_turns_when_forward_motion_is_blocked(self):
        player = make_player((Box((0, 1.5, -.55), (3, 3, .2)),))
        for _ in range(10):
            player.update(.1, InputState(forward=1))
        self.assertGreater(player.body.position.z, -.3)
        previous_rotation = player.transform.rotation
        player.update(.1, InputState(right=1))
        self.assertNotEqual(player.transform.rotation, previous_rotation)

    def test_camera_models_are_hidden_during_gameplay_without_building_markers(self):
        player = make_player()
        with patch("game.entities.player.camera_model_boxes") as markers:
            player.update(.1, InputState())
            self.assertIsNotNone(player._active_fixed_camera())
            self.assertEqual(player.camera_marker_boxes, ())
            markers.assert_not_called()


if __name__ == "__main__":
    unittest.main()
