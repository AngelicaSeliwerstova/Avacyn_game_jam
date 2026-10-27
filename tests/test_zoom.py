import math
import unittest

import glm

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.controllers.first_person import FirstPersonController
from engine.input.state import InputState
from engine.scene.box import Box
from engine.scene.camera import Camera
from engine.scene.interaction import Interaction
from engine.scene.level import Level
from game.entities.player import create_player


def make_controller(**zoom_settings):
    camera = Camera((0, 1.6, 4), (0, 1.6, 3), 60, 0.1, 100)
    controller = FirstPersonController(camera, 2.5, 0.12, 80, 0.1, 0.25, 0.1,
                                      **{"zoom_fov_degrees": 35, "zoom_speed": 12, **zoom_settings})
    return camera, controller


class ZoomTests(unittest.TestCase):
    def test_smooth_zoom_and_return_match_at_different_frame_rates(self):
        halfway = []
        for fps in (30, 60, 120):
            camera, controller = make_controller()
            controller.update(0, zoom=True)
            self.assertEqual(camera.fov_degrees, 60)
            for frame in range(fps):
                previous = camera.fov_degrees
                controller.update(1 / fps, zoom=True)
                self.assertTrue(35 <= camera.fov_degrees <= previous)
                if frame == fps // 2 - 1:
                    halfway.append(camera.fov_degrees)
            self.assertEqual(camera.fov_degrees, 35)
            for _ in range(fps):
                previous = camera.fov_degrees
                controller.update(1 / fps)
                self.assertTrue(previous <= camera.fov_degrees <= 60)
            self.assertEqual(camera.fov_degrees, 60)
        for fov in halfway:
            self.assertAlmostEqual(fov, halfway[0], places=10)

    def test_release_during_transition_reverses_smoothly(self):
        camera, controller = make_controller()
        controller.update(1 / 60, zoom=True)
        pressed = camera.fov_degrees
        self.assertTrue(35 < pressed < 60)
        controller.update(1 / 60)
        self.assertTrue(pressed < camera.fov_degrees < 60)

    def test_mouse_turn_scales_with_current_field_of_view(self):
        normal, normal_controller = make_controller()
        zoomed, zoom_controller = make_controller()
        for _ in range(60):
            normal_controller.update(1 / 60)
            zoom_controller.update(1 / 60, zoom=True)
        yaw = normal_controller.yaw_degrees
        normal_controller.update(0, mouse_delta=(10, 10))
        zoom_controller.update(0, mouse_delta=(10, 10), zoom=True)
        ratio = math.tan(math.radians(zoomed.fov_degrees) / 2) / math.tan(math.radians(normal.fov_degrees) / 2)
        self.assertAlmostEqual(zoom_controller.yaw_degrees - yaw,
                               (normal_controller.yaw_degrees - yaw) * ratio, places=8)
        self.assertAlmostEqual(zoom_controller.pitch_degrees, normal_controller.pitch_degrees * ratio, places=8)

    def test_zoom_keeps_physics_stance_and_camera_position(self):
        level = Level((30, 30), 1, (), (0, 1.6, 4), (0, 1.6, 3), ((80, 80, 80),) * 2)
        normal, zoomed = (create_player(level, CollisionWorld3D(())) for _ in range(2))
        for frame in range(120):
            values = dict(forward=1, right=1, sprint=frame < 20, jump=frame == 0, crouch=frame >= 50)
            normal.update(1 / 60, InputState(**values))
            zoomed.update(1 / 60, InputState(**values, zoom=True))
            self.assertEqual(normal.body.position, zoomed.body.position)
            self.assertEqual(normal.body.height, zoomed.body.height)
            self.assertEqual(normal.camera.position, zoomed.camera.position)
            self.assertLess(glm.length(normal.camera.target - zoomed.camera.target), 1e-6)
        self.assertEqual(zoomed.camera.fov_degrees, settings.CAMERA_ZOOM_FOV_DEGREES)

    def test_zoom_does_not_extend_interaction_reach(self):
        crate = Box((0, 1, 0), (1, 2, 1), interaction=Interaction("Crate", "Closed"))
        level = Level((20, 20), 1, (crate,), (0, 1.6, 4), (0, 1.6, 3), ((80, 80, 80),) * 2)
        player = create_player(level, CollisionWorld3D((crate.collider,)))
        for _ in range(60):
            player.update(1 / 60, InputState(zoom=True, interact=True))
        self.assertEqual(player.aim_text, "")
        for _ in range(36):
            player.update(1 / 60, InputState(forward=1, zoom=True))
        self.assertIn("[E]", player.aim_text)

    def test_invalid_zoom_settings_are_rejected(self):
        for value in (0, -1, 61, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                make_controller(zoom_fov_degrees=value)
        for speed in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                make_controller(zoom_speed=speed)
