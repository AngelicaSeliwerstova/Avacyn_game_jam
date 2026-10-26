import unittest

import glm

from engine.collision.aabb import AABB
from engine.collision.aabb3d import AABB3D
from engine.collision.world3d import CollisionWorld3D
from engine.controllers.first_person import FirstPersonController
from engine.physics.character import CharacterBody
from engine.scene.camera import Camera
from game.levels import create_level


def make_body(world, position=(0, 0, 3), step_height=0.3):
    return CharacterBody(position, world, radius=0.25, height=1.8,
                         step_height=step_height, gravity=18, collision_max_step=0.1,
                         physics_step=1 / 120, camera_smoothing=12)


def advance(body, seconds, fps=60, velocity=(0, 0, 0)):
    for _ in range(round(seconds * fps)):
        body.update(1 / fps, glm.vec3(velocity))


class CharacterTests(unittest.TestCase):
    def setUp(self):
        self.level = create_level("stairs")
        self.world = CollisionWorld3D((box.collider for box in self.level.boxes), self.level.floor_bounds)

    def test_climb_landing_and_descend_at_different_frame_rates(self):
        results = []
        for fps in (30, 60, 120):
            body = make_body(self.world, (0, 0, 6))
            advance(body, 4, fps, (0, 0, -2.5))
            self.assertAlmostEqual(body.position.y, 1.5, places=5)
            self.assertTrue(body.grounded)
            results.append(body.position)
            advance(body, 4, fps, (0, 0, 2.5))
            self.assertAlmostEqual(body.position.y, 0, places=5)
            self.assertAlmostEqual(body.position.z, 6, places=4)
            self.assertTrue(body.grounded)
        for result in results[1:]:
            self.assertLess(glm.length(result - results[0]), 1e-5)

    def test_fall_from_landing_and_cannot_climb_its_side(self):
        for fps in (30, 60, 120):
            body = make_body(self.world, (0, 1.5, -4))
            advance(body, 1.2, fps, (2.5, 0, 0))
            self.assertFalse(body.grounded)
            self.assertTrue(0 < body.position.y < 1.5)
            advance(body, 0.8, fps)
            self.assertAlmostEqual(body.position.y, 0, places=5)
            self.assertTrue(body.grounded)
            advance(body, 2, fps, (-2.5, 0, 0))
            self.assertGreaterEqual(body.position.x, 2.75 - 1e-5)
            self.assertAlmostEqual(body.position.y, 0, places=5)

    def test_airborne_character_does_not_step_up(self):
        world = CollisionWorld3D((AABB3D(AABB(-2, -2, 2, 1), 0, 0.25),))
        result = world.move_horizontal(glm.vec3(0, 0.1, 1.3), glm.vec3(0, 0, -1),
                                       0.25, 1.8, 0.1, 0.3, grounded=False)
        self.assertAlmostEqual(result.z, 1.25, places=5)
        self.assertAlmostEqual(result.y, 0.1, places=5)

    def test_low_ceiling_blocks_step_up_but_allows_floor_walking(self):
        step = AABB3D(AABB(-2, -1, 2, 1), 0, 0.25)
        roof = AABB3D(AABB(-2, -2, 2, 4), 2.0, 2.2)
        world = CollisionWorld3D((step, roof))
        body = make_body(world)
        advance(body, 2, velocity=(0, 0, -2.5))
        self.assertAlmostEqual(body.position.z, 1.25, places=5)
        self.assertAlmostEqual(body.position.y, 0, places=5)
        open_world = CollisionWorld3D((step,))
        body = make_body(open_world)
        advance(body, 1, velocity=(0, 0, -2.5))
        self.assertAlmostEqual(body.position.y, 0.25, places=5)

    def test_vertical_sweep_catches_thin_floor_and_ceiling(self):
        platform = AABB3D(AABB(-2, -2, 2, 2), 1, 1.001)
        roof = AABB3D(AABB(-2, -2, 2, 2), 4, 4.001)
        world = CollisionWorld3D((platform, roof))
        landed, hit = world.move_vertical(glm.vec3(0, 2, 0), -10, 0.25, 1.8)
        self.assertTrue(hit)
        self.assertAlmostEqual(landed.y, 1.001, places=5)
        stopped, hit = world.move_vertical(landed, 10, 0.25, 1.8)
        self.assertTrue(hit)
        self.assertAlmostEqual(stopped.y, 2.2, places=5)

    def test_body_can_walk_below_a_platform_and_stand_on_it(self):
        bridge = AABB3D(AABB(-2, -2, 2, 2), 2, 2.3)
        world = CollisionWorld3D((bridge,))
        body = make_body(world)
        advance(body, 1, velocity=(0, 0, -2.5))
        self.assertAlmostEqual(body.position.z, 0.5, places=4)
        self.assertAlmostEqual(body.position.y, 0, places=5)
        on_top = make_body(world, (0, 2.3, 0))
        advance(on_top, 1)
        self.assertTrue(on_top.grounded)
        self.assertAlmostEqual(on_top.position.y, 2.3, places=5)

    def test_spawn_checks_full_body_and_allows_spawn_in_air(self):
        roof = AABB3D(AABB(-2, -2, 2, 2), 1.7, 2)
        with self.assertRaisesRegex(ValueError, "spawn"):
            make_body(CollisionWorld3D((roof,)), (0, 0, 0))
        body = make_body(CollisionWorld3D(()), (0, 5, 0))
        advance(body, 2)
        self.assertAlmostEqual(body.position.y, 0, places=5)
        self.assertTrue(body.grounded)

    def test_controller_smooths_camera_and_keeps_look_direction(self):
        step = AABB3D(AABB(-2, -2, 2, 1), 0, 0.25)
        world = CollisionWorld3D((step,))
        body = make_body(world, (0, 0, 1.3))
        camera = Camera((0, 1.6, 1.3), (0, 1.6, 0), 60, 0.1, 100)
        controller = FirstPersonController(camera, 2.5, 0.12, 80, 0.1, 0.25, 0.1,
                                          body=body, eye_height=1.6)
        controller.update(1 / 30, forward_axis=1)
        self.assertAlmostEqual(body.position.y, 0.25, places=5)
        self.assertTrue(1.6 < camera.position.y < 1.85)
        for _ in range(120):
            controller.update(1 / 120)
        self.assertAlmostEqual(camera.position.y, 1.85, places=4)
        direction = camera.target - camera.position
        self.assertLess(glm.length(direction - glm.vec3(0, 0, -1)), 1e-5)
        self.assertFalse(world.is_blocked(body.position, body.radius, body.height))

    def test_tall_wall_sliding_and_thin_wall_sweep(self):
        wall = AABB3D(AABB(0, -5, 0.001, 5), 0, 5)
        world = CollisionWorld3D((wall,))
        body = make_body(world, (-2, 0, 0))
        advance(body, 1, velocity=(4, 0, 1))
        self.assertAlmostEqual(body.position.x, -0.25, places=5)
        self.assertAlmostEqual(body.position.z, 1, places=4)
        self.assertAlmostEqual(body.position.y, 0, places=5)

    def test_existing_corridor_route_with_character_physics(self):
        level = create_level("corridor")
        world = CollisionWorld3D((box.collider for box in level.boxes), level.floor_bounds)
        body = make_body(world, (-6, 0, 7))
        for velocity, expected in (
            ((0, 0, -2.5), (-6, 0, -6)),
            ((2.5, 0, 0), (7, 0, -6)),
            ((-2.5, 0, 0), (-6, 0, -6)),
            ((0, 0, 2.5), (-6, 0, 7)),
        ):
            advance(body, 5.2, velocity=velocity)
            self.assertLess(glm.length(body.position - glm.vec3(expected)), 0.002)
            self.assertTrue(body.grounded)
            self.assertFalse(world.is_blocked(body.position, body.radius - 1e-5, body.height))


if __name__ == "__main__":
    unittest.main()
