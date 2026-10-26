import math
import unittest

import glm

from engine.controllers.first_person import FirstPersonController
from engine.scene.camera import Camera


def make_controller():
    camera = Camera((0, 1.6, 0), (0, 1.6, -1), 60, 0.1, 100)
    controller = FirstPersonController(
        camera, move_speed=2.5, mouse_sensitivity=1.0,
        pitch_limit_degrees=80.0, max_delta_time=0.1,
    )
    return camera, controller


class FirstPersonTests(unittest.TestCase):
    def test_ten_second_distance_at_different_frame_rates(self):
        for fps in (30, 60, 120):
            with self.subTest(fps=fps):
                camera, controller = make_controller()
                start = glm.vec3(camera.position)
                for _ in range(fps * 10):
                    controller.update(1 / fps, forward_axis=1)
                self.assertAlmostEqual(glm.length(camera.position - start), 25.0, places=2)

    def test_diagonal_distance_matches_straight_distance(self):
        for forward, right in ((1, 0), (1, 1), (-1, -1)):
            with self.subTest(forward=forward, right=right):
                camera, controller = make_controller()
                start = glm.vec3(camera.position)
                for _ in range(60):
                    controller.update(1 / 60, forward, right)
                self.assertAlmostEqual(glm.length(camera.position - start), 2.5, places=4)

    def test_looking_up_and_down_keeps_height_and_walking_speed(self):
        for mouse_y, expected_pitch in ((-1000, 80), (1000, -80)):
            with self.subTest(mouse_y=mouse_y):
                camera, controller = make_controller()
                start = glm.vec3(camera.position)
                controller.update(0, mouse_delta=(0, mouse_y))
                direction = glm.normalize(camera.target - camera.position)
                self.assertAlmostEqual(math.degrees(math.asin(direction.y)), expected_pitch, places=3)
                for _ in range(60):
                    controller.update(1 / 60, forward_axis=1)
                self.assertAlmostEqual(camera.position.y, 1.6, places=5)
                self.assertAlmostEqual(glm.length(camera.position - start), 2.5, places=4)
                camera.view_matrix  # Камера остаётся пригодной для отрисовки.

    def test_mouse_turn_changes_walking_direction_without_orbiting(self):
        camera, controller = make_controller()
        controller.update(0, mouse_delta=(90, 0))
        controller.update(0.1, forward_axis=1)
        self.assertAlmostEqual(camera.position.x, 0.25, places=5)
        self.assertAlmostEqual(camera.position.z, 0.0, places=5)
        direction = camera.target - camera.position
        self.assertAlmostEqual(direction.x, 1.0, places=5)
        self.assertAlmostEqual(direction.z, 0.0, places=5)

    def test_same_mouse_travel_has_same_turn_at_different_frame_rates(self):
        directions = []
        for fps, pixels_per_frame in ((30, 4), (60, 2), (120, 1)):
            camera, controller = make_controller()
            for _ in range(fps):
                controller.update(1 / fps, mouse_delta=(pixels_per_frame, 0))
            directions.append(camera.target - camera.position)
        for direction in directions[1:]:
            self.assertLess(glm.length(direction - directions[0]), 1e-5)

    def test_long_stall_limits_the_movement_step(self):
        camera, controller = make_controller()
        start = glm.vec3(camera.position)
        controller.update(5.0, forward_axis=1)
        self.assertAlmostEqual(glm.length(camera.position - start), 0.25, places=5)
