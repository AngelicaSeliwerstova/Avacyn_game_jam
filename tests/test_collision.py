import random
import unittest

import glm

from engine.collision.aabb import AABB
from engine.collision.world import CollisionWorld
from engine.controllers.first_person import FirstPersonController
from engine.scene.camera import Camera


class CollisionTests(unittest.TestCase):
    def setUp(self):
        self.box = AABB(-1, -1, 1, 1)
        self.world = CollisionWorld((self.box,))

    def test_circle_has_rounded_corners(self):
        self.assertFalse(self.box.intersects_circle(1.2, 1.2, 0.25))
        self.assertTrue(self.box.intersects_circle(1.15, 1.15, 0.25))
        self.assertFalse(self.box.intersects_circle(1.25, 0, 0.25))

    def test_large_movements_stop_at_each_cube_face(self):
        cases = (
            ((-4, 1.6, 0), (12, 0, 0), (-1.25, 1.6, 0)),
            ((4, 1.6, 0), (-12, 0, 0), (1.25, 1.6, 0)),
            ((0, 1.6, -4), (0, 0, 12), (0, 1.6, -1.25)),
            ((0, 1.6, 4), (0, 0, -12), (0, 1.6, 1.25)),
        )
        for position, movement, expected in cases:
            with self.subTest(position=position):
                result = self.world.move(glm.vec3(position), glm.vec3(movement), 0.25, 0.1)
                self.assertLess(glm.length(result - glm.vec3(expected)), 1e-5)

    def test_diagonal_movement_slides_along_face(self):
        result = self.world.move(glm.vec3(-2, 1.6, 0), glm.vec3(3, 0, 1), 0.25, 0.1)
        self.assertAlmostEqual(result.x, -1.25, places=5)
        self.assertAlmostEqual(result.z, 1.0, places=5)

    def test_round_corner_contact_uses_circle_radius(self):
        result = self.world.move(glm.vec3(-2, 1.6, 1.2), glm.vec3(4, 0, 0), 0.25, 0.1)
        self.assertAlmostEqual(result.x, -1.15, places=5)

    def test_thin_wall_cannot_be_skipped(self):
        world = CollisionWorld((AABB(0, -5, 0.001, 5),))
        result = world.move(glm.vec3(-2, 1.6, 0), glm.vec3(4, 0, 0), 0.25, 10.0)
        self.assertAlmostEqual(result.x, -0.25, places=5)

    def test_two_walls_block_their_shared_corner(self):
        world = CollisionWorld((AABB(0, -5, 1, 1), AABB(-5, 0, 1, 1)))
        result = world.move(glm.vec3(-2, 1.6, -2), glm.vec3(4, 0, 4), 0.25, 0.1)
        self.assertAlmostEqual(result.x, -0.25, places=5)
        self.assertAlmostEqual(result.z, -0.25, places=5)

    def test_radius_changes_stopping_distance(self):
        for radius in (0.1, 0.25, 0.5):
            with self.subTest(radius=radius):
                result = self.world.move(glm.vec3(0, 1.6, 4), glm.vec3(0, 0, -8), radius, 0.1)
                self.assertAlmostEqual(result.z, 1 + radius, places=5)

    def test_floor_bounds_keep_entire_player_on_floor(self):
        world = CollisionWorld((), bounds=AABB(-5, -5, 5, 5))
        result = world.move(glm.vec3(0, 1.6, 0), glm.vec3(20, 0, -20), 0.25, 0.1)
        self.assertAlmostEqual(result.x, 4.75, places=5)
        self.assertAlmostEqual(result.z, -4.75, places=5)
        self.assertAlmostEqual(result.y, 1.6, places=5)

    def test_mixed_movements_do_not_enter_obstacles(self):
        world = CollisionWorld(
            (AABB(-1, -1, 1, 1), AABB(2, -4, 2.01, 4), AABB(-5, 2, 0, 3)),
            bounds=AABB(-8, -8, 8, 8),
        )
        rng = random.Random(42)
        position = glm.vec3(-5, 1.6, -5)
        for _ in range(500):
            movement = glm.vec3(rng.uniform(-4, 4), 0, rng.uniform(-4, 4))
            position = world.move(position, movement, 0.25, 0.1)
            # Разрешаем только погрешность округления glm.vec3 до float32.
            self.assertFalse(world.is_blocked(position, 0.25 - 1e-5))

    def test_controller_stops_at_same_distance_at_different_frame_rates(self):
        for fps in (30, 60, 120):
            with self.subTest(fps=fps):
                camera = Camera((0, 1.6, 4), (0, 1.6, 0), 60, 0.1, 100)
                controller = FirstPersonController(
                    camera, 2.5, 0.12, 80, 0.1,
                    player_radius=0.25, collision_max_step=0.1, collision_world=self.world,
                )
                for _ in range(fps * 5):
                    controller.update(1 / fps, forward_axis=1)
                self.assertAlmostEqual(camera.position.z, 1.25, places=5)
                self.assertAlmostEqual(camera.position.y, 1.6, places=5)

    def test_player_cannot_spawn_partly_inside_cube(self):
        camera = Camera((1.1, 1.6, 0), (0, 1.6, 0), 60, 0.1, 100)
        with self.assertRaisesRegex(ValueError, "spawn"):
            FirstPersonController(
                camera, 2.5, 0.12, 80, 0.1,
                player_radius=0.25, collision_max_step=0.1, collision_world=self.world,
            )
