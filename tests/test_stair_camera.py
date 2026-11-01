from dataclasses import replace
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import glm

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.input.state import InputState
from game.campaign import Campaign
from game.entities.player import create_player
from game.entities.stair_camera import StairCameraShake
from game.levels import create_level
from game.levels.spiral import SpiralStair
from support_levels import create_level as fixture_level
from support_story import finish_conversation
from test_hospital import make_body


class StairCameraTests(unittest.TestCase):
    def setUp(self):
        model = patch.object(settings, "PLAYER_MODEL", None)
        model.start()
        self.addCleanup(model.stop)

    def player(self, level=None):
        level = fixture_level("stairs") if level is None else level
        level = replace(level, stair_surfaces=level.boxes)
        world = CollisionWorld3D((box.collider for box in level.boxes), level.floor_bounds)
        return create_player(level, world)

    def test_shake_tracks_real_steps_on_both_flights_not_the_ground_beneath_them(self):
        level = create_level("start")
        world = CollisionWorld3D((box.collider for box in level.collision_boxes), level.floor_bounds)
        shake = StairCameraShake(level.stair_surfaces)
        path = SpiralStair().walking_path()
        def body_at(index):
            x, y, z = path[index]
            support = world.support_height(glm.vec3(x, y, z), 0.25, y + 0.3)
            return make_body(world, (x, support, z))
        for index in (9, 18, 28, 45, 53, 65):
            with self.subTest(step=index):
                body = body_at(index)
                self.assertTrue(shake.on_stairs(body))
        x, _, z = path[25]
        self.assertFalse(shake.on_stairs(make_body(world, (x, 0, z))))
        self.assertFalse(shake.on_stairs(make_body(world, (3.5, 0, 10))))
        body = body_at(18)
        body.grounded = False
        self.assertFalse(shake.on_stairs(body))

    def test_visible_shake_keeps_controls_physics_and_interaction_camera_stable(self):
        player, reference = self.player(), self.player()
        peak, matrix_changed = 0, False
        for _ in range(150):
            player.update(1 / 60, InputState(forward=1))
            with patch.object(settings, "STAIR_SHAKE_ENABLED", False):
                reference.update(1 / 60, InputState(forward=1))
            peak = max(peak, *(abs(angle) for angle in player.camera.view_rotation_degrees))
            matrix_changed |= player.camera.view_matrix != reference.camera.view_matrix
            self.assertEqual(player.body.position, reference.body.position)
            self.assertEqual(player.camera.position, reference.camera.position)
            self.assertEqual(player.camera.target, reference.camera.target)
            self.assertEqual(player._interaction_camera.target, reference._interaction_camera.target)
        self.assertGreater(peak, 0.15)
        self.assertLess(peak, 0.4)
        self.assertGreater(player.stair_stress_strength, 0.7)
        self.assertTrue(matrix_changed)
        self.assertNotIn("stairs_walk_finished", player.story_events)
        for _ in range(50):
            player.update(1 / 60, InputState())
        self.assertEqual(player.camera.view_rotation_degrees, (0, 0, 0))
        self.assertIn("stairs_walk_finished", player.story_events)
        self.assertGreater(player.stair_stress_strength, 0)
        for _ in range(150):
            player.update(1 / 60, InputState())
        self.assertEqual(player.stair_stress_strength, 0)

    def test_standing_on_steps_and_a_brief_touch_do_not_produce_a_comment(self):
        surface = fixture_level("stairs").boxes[0]
        shake = StairCameraShake((surface,))
        body = SimpleNamespace(position=glm.vec3(0, surface.collider.top, surface.position[2]),
                               radius=0.25, grounded=True, horizontal_speed=0)
        for _ in range(90):
            rotation, event = shake.update(1 / 60, body)
            self.assertEqual(rotation, (0, 0, 0))
            self.assertFalse(event)
        body.horizontal_speed = 2
        for _ in range(15):
            shake.update(1 / 60, body)
        body.horizontal_speed = 0
        for _ in range(90):
            _, event = shake.update(1 / 60, body)
            self.assertFalse(event)

    def test_entering_creator_clears_the_shake(self):
        with tempfile.TemporaryDirectory() as folder:
            level = replace(fixture_level("stairs"), camera_save_path=Path(folder) / "cameras.json")
            player = self.player(level)
            for _ in range(150):
                player.update(1 / 60, InputState(forward=1))
            self.assertGreater(player._stair_shake.strength, 0)
            player.update(1 / 60, InputState(toggle_camera_editor=True))
            self.assertTrue(player.creator_mode)
            self.assertEqual(player.camera.view_rotation_degrees, (0, 0, 0))
            self.assertEqual(player._stair_shake.strength, 0)
            self.assertEqual(player.stair_stress_strength, 0)

    def test_stress_envelope_is_frame_rate_independent_and_recovers_fully(self):
        surface = fixture_level("stairs").boxes[0]
        body = SimpleNamespace(position=glm.vec3(0, surface.collider.top, surface.position[2]),
                               radius=0.25, grounded=True, horizontal_speed=2)
        values = []
        for fps in (30, 60, 120):
            shake = StairCameraShake((surface,))
            body.horizontal_speed = 2
            for _ in range(fps):
                shake.update(1 / fps, body)
            values.append(shake.stress)
            body.horizontal_speed = 0
            for _ in range(fps * 3):
                shake.update(1 / fps, body)
            self.assertEqual(shake.stress, 0)
        self.assertGreater(values[0], 0)
        self.assertLess(values[0], 1)
        for value in values[1:]:
            self.assertAlmostEqual(value, values[0])

    def test_story_comment_waits_for_dialogue_then_plays_once_as_the_heroine(self):
        scene = Campaign().load_level("start")
        session = scene.session
        scene.session._flags.add("act0:key_taken")
        scene.player.body._position = glm.vec3(-10.2, 1, 3.3)
        session.update(0)
        self.assertNotIn("act0:scratched", session._flags)
        self.assertEqual(scene.player.story_status, "")
        finish_conversation(session)
        session.update(0)
        self.assertIsNone(session.dialog)
        self.assertEqual(scene.player.story_status,
                         "Героиня: Ай, чёрт! Поцарапалась об какой-то гвоздь... Ещё и ржавый и окровавленный. Интересно, почему он в крови?")
        self.assertIn("act0:scratched", session._flags)
        session.update(10)
        session.update(0)
        self.assertEqual(scene.player.story_status, "")


if __name__ == "__main__":
    unittest.main()
