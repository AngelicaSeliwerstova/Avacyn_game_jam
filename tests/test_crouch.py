import unittest

import glm

from config import settings
from engine.collision.aabb import AABB
from engine.collision.aabb3d import AABB3D
from engine.collision.world3d import CollisionWorld3D
from engine.controllers.first_person import FirstPersonController
from engine.input.state import InputState
from engine.physics.character import CharacterBody
from engine.scene.camera import Camera
from engine.scene.level import Level
from game.entities.player import create_player
from game.entities.player_state import MovementState
from game.levels import create_level


def make_character(world, position=(0, 0, 3)):
    body = CharacterBody(position, world, radius=0.25, height=1.8, step_height=0.3,
                         gravity=18, collision_max_step=0.1, physics_step=1 / 120,
                         camera_smoothing=12, jump_height=0.9, crouch_height=1.0,
                         stance_speed=5)
    x, y, z = position
    camera = Camera((x, y + 1.6, z), (x, y + 1.6, z - 1), 60, 0.1, 100)
    controller = FirstPersonController(camera, 2.5, 0.12, 80, 0.1, 0.25, 0.1,
                                      body=body, sprint_speed=5, crouch_speed=1.25,
                                      crouch_eye_height=0.85)
    return body, camera, controller


class CrouchTests(unittest.TestCase):
    def test_stance_moves_smoothly_keeps_feet_and_recovers_at_different_fps(self):
        for fps in (30, 60, 120):
            body, camera, controller = make_character(CollisionWorld3D(()))
            controller.update(1 / fps, crouch=True)
            self.assertTrue(1 < body.height < 1.8)
            self.assertTrue(0.85 < camera.position.y < 1.6)
            for _ in range(fps):
                controller.update(1 / fps, crouch=True)
                self.assertAlmostEqual(body.position.y, 0)
                self.assertLess(camera.position.y, body.height)
            self.assertAlmostEqual(body.height, 1)
            self.assertAlmostEqual(camera.position.y, 0.85, places=5)
            for _ in range(fps):
                controller.update(1 / fps)
            self.assertFalse(body.is_crouching)
            self.assertAlmostEqual(body.height, 1.8)
            self.assertAlmostEqual(camera.position.y, 1.6, places=5)
            self.assertLess(glm.length(camera.target - camera.position - glm.vec3(0, 0, -1)), 1e-5)

    def test_crouch_speed_overrides_sprint_and_normalizes_diagonal(self):
        for fps in (30, 60, 120):
            for diagonal in (0, 1):
                body, _, controller = make_character(CollisionWorld3D(()))
                start = body.position
                for _ in range(fps):
                    controller.update(1 / fps, forward_axis=1, right_axis=diagonal,
                                      crouch=True, sprint=True)
                self.assertAlmostEqual(glm.length(body.position - start), 1.25, places=4)

    def test_low_passage_blocks_standing_until_the_whole_body_is_clear(self):
        roof = AABB3D(AABB(-2, -2, 2, 1), 1.2, 1.4)
        world = CollisionWorld3D((roof,))
        for fps in (30, 60, 120):
            body, camera, controller = make_character(world)
            for _ in range(3 * fps):
                controller.update(1 / fps, forward_axis=1, crouch=True)
                self.assertFalse(world.is_blocked(body.position, body.radius, body.height))
            for _ in range(fps // 2):
                controller.update(1 / fps, forward_axis=1, sprint=True)
                self.assertAlmostEqual(body.height, 1)
                self.assertAlmostEqual(camera.position.y, 0.85, places=5)
                self.assertAlmostEqual(body.horizontal_speed, 1.25, places=3)
            for _ in range(2 * fps):
                controller.update(1 / fps, forward_axis=1, sprint=True)
                self.assertFalse(world.is_blocked(body.position, body.radius, body.height))
            self.assertLess(body.position.z, -2.25)
            self.assertFalse(body.is_crouching)
            self.assertAlmostEqual(camera.position.y, 1.6, places=5)

    def test_crouching_jump_respects_ceiling_and_can_still_land(self):
        roof = AABB3D(AABB(-2, -2, 2, 4), 1.2, 1.4)
        for fps in (30, 60, 120):
            # Входим в низкий проход уже в приседе.
            body, _, controller = make_character(CollisionWorld3D(()))
            for _ in range(fps):
                controller.update(1 / fps, crouch=True)
            body.world = CollisionWorld3D((roof,))
            peak = 0
            for frame in range(fps):
                controller.update(1 / fps, crouch=True, jump=frame == 0)
                peak = max(peak, body.position.y)
                self.assertFalse(body.world.is_blocked(body.position, body.radius, body.height))
            self.assertAlmostEqual(peak, 0.2, delta=0.01)
            self.assertTrue(body.grounded)

    def test_crouching_climbs_and_descends_existing_stairs(self):
        level = create_level("stairs")
        world = CollisionWorld3D((b.collider for b in level.boxes), level.floor_bounds)
        for fps in (30, 60, 120):
            body, camera, controller = make_character(world, (0, 0, 6))
            for direction, height in ((1, 1.5), (-1, 0)):
                for _ in range(8 * fps):
                    controller.update(1 / fps, forward_axis=direction, crouch=True)
                    self.assertFalse(world.is_blocked(body.position, body.radius - 1e-5, body.height))
                    self.assertLess(camera.position.y, body.position.y + body.height)
                self.assertAlmostEqual(body.position.y, height, places=5)
                self.assertTrue(body.grounded)

    def test_airborne_control_press_does_not_change_stance_view_or_speed(self):
        for fps in (30, 60, 120):
            for simultaneous in (False, True):
                body, camera, controller = make_character(CollisionWorld3D(()))
                reference, _, reference_controller = make_character(CollisionWorld3D(()))
                airborne_frames = 0
                for frame in range(fps):
                    # Нажимаем либо вместе с прыжком, либо уже в полёте; отпускаем до посадки.
                    crouch = (simultaneous or frame >= fps // 10) and frame < fps // 4
                    controller.update(1 / fps, forward_axis=1, sprint=True,
                                      jump=frame == 0, crouch=crouch)
                    reference_controller.update(1 / fps, forward_axis=1, sprint=True,
                                                jump=frame == 0)
                    self.assertAlmostEqual(body.height, 1.8)
                    self.assertAlmostEqual(camera.position.y - body.position.y, 1.6, places=5)
                    self.assertLess(glm.length(body.position - reference.position), 1e-5)
                    airborne_frames += not body.grounded
                self.assertGreater(airborne_frames, fps // 2)
                self.assertTrue(body.grounded)

    def test_release_in_air_preserves_crouch_until_landing(self):
        for fps in (30, 60, 120):
            for transition in (False, True):
                body, camera, controller = make_character(CollisionWorld3D(()))
                for _ in range(1 if transition else fps):
                    controller.update(1 / fps, crouch=True)
                takeoff_height = body.height
                takeoff_eye_height = camera.position.y - body.position.y
                controller.update(1 / fps, jump=True)  # Ctrl отпущен вместе с прыжком.
                frames = 0
                while not body.grounded:
                    self.assertAlmostEqual(body.height, takeoff_height)
                    self.assertAlmostEqual(camera.position.y - body.position.y, takeoff_eye_height, places=5)
                    controller.update(1 / fps)
                    frames += 1
                    self.assertLess(frames, fps * 2)
                for _ in range(fps):
                    controller.update(1 / fps)
                self.assertFalse(body.is_crouching)
                self.assertAlmostEqual(camera.position.y - body.position.y, 1.6, places=5)

    def test_control_held_during_fall_starts_crouch_only_after_landing(self):
        for fps in (30, 60, 120):
            body, camera, controller = make_character(CollisionWorld3D(()), (0, 3, 0))
            frames = 0
            while not body.grounded:
                self.assertAlmostEqual(body.height, 1.8)
                self.assertAlmostEqual(camera.position.y - body.position.y, 1.6, places=5)
                controller.update(1 / fps, crouch=True)
                frames += 1
                self.assertLess(frames, fps * 2)
            for _ in range(fps):
                controller.update(1 / fps, crouch=True)
            self.assertAlmostEqual(body.height, 1)
            self.assertAlmostEqual(camera.position.y, 0.85, places=5)

    def test_player_wires_settings_and_reports_actual_stance_even_when_idle(self):
        level = Level((10, 10), 1, (), (0, 1.6, 0), (0, 1.6, -1), ((80, 80, 80),) * 2)
        player = create_player(level, CollisionWorld3D(()))
        for _ in range(30):
            player.update(1 / 60, InputState(crouch=True))
        self.assertAlmostEqual(player.body.height, settings.PLAYER_CROUCH_HEIGHT)
        self.assertIn("CROUCH", "\n".join(player.debug_lines))
        player.update(1 / 60, InputState(forward=1, sprint=True, crouch=True))
        self.assertEqual(player.movement_state, MovementState.CROUCHING)
        self.assertAlmostEqual(player.body.horizontal_speed, settings.CROUCH_SPEED, places=4)
        for _ in range(30):
            player.update(1 / 60, InputState())
        self.assertIn("STAND", "\n".join(player.debug_lines))

    def test_invalid_stance_parameters_are_rejected(self):
        for crouch_height in (0, -1, 2, float("nan"), float("inf")):
            with self.subTest(height=crouch_height), self.assertRaises(ValueError):
                CharacterBody((0, 0, 0), CollisionWorld3D(()), 0.25, 1.8, 0.3, 18,
                              0.1, 1 / 120, 12, 0.9, crouch_height=crouch_height)


if __name__ == "__main__":
    unittest.main()
