from dataclasses import replace
import unittest
from unittest.mock import patch

import glm

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.input.state import InputState
from game.entities.player import create_player
from game.levels import create_level
from game.levels.maze import maze_layout_path
from game.levels.maze_layout import load_maze_layout


class BasementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.level = create_level("maze")
        cls.layout = load_maze_layout(maze_layout_path())
        cls.world = CollisionWorld3D((box.collider for box in cls.level.boxes), cls.level.floor_bounds,
                                    cls.level.base_height)

    def walk(self, player, points, fps):
        for target in points:
            for _ in range(fps * 30):
                position = player.body.position
                delta = glm.vec3(target[0] - position.x, 0, target[2] - position.z)
                distance = glm.length(delta)
                if distance < 0.003:
                    break
                player.body.update(1 / fps, delta / distance * min(settings.SPRINT_SPEED, distance * fps))
                self.assertFalse(self.world.is_blocked(player.body.position, player.body.radius - 1e-5, player.body.height))
            else:
                self.fail(f"Cannot reach {target}: {player.body.position}")
            self.assertAlmostEqual(player.body.position.y, target[1], places=2)

    def test_descent_room_and_return_work_with_real_physics(self):
        stairs = self.layout.basement.stair_points(self.layout)
        room = (0, self.level.base_height, stairs[0][2])
        for fps in (30, 60, 120):
            with self.subTest(fps=fps):
                player = create_player(self.level, self.world)
                self.walk(player, (*reversed(stairs), room), fps)
                self.walk(player, (*stairs, (self.level.spawn_position[0], 0, self.level.spawn_position[2])), fps)
                self.assertTrue(player.body.grounded)

    def test_room_is_open_and_has_225_lamps_above_walkable_floor(self):
        lamps = self.layout.basement.lights(self.layout)
        self.assertEqual(len(lamps), 225)
        for light in lamps:
            point = glm.vec3(light.position[0], self.level.base_height, light.position[2])
            self.assertFalse(self.world.is_blocked(point, settings.PLAYER_RADIUS, settings.PLAYER_HEIGHT))
            self.assertAlmostEqual(self.world.support_height(point, settings.PLAYER_RADIUS, point.y), point.y, places=6)
            self.assertGreater(light.position[1], point.y + settings.PLAYER_HEIGHT)
        self.assertGreater(len(self.level.lighting.lights), 128)

    def test_floor_label_and_jump_obey_negative_height_and_ceiling(self):
        y = self.level.base_height
        level = replace(self.level, spawn_position=(0, y + settings.PLAYER_EYE_HEIGHT, 0),
                        spawn_target=(0, y + settings.PLAYER_EYE_HEIGHT, -1))
        with patch.object(settings, "JUMP_HEIGHT", 12):
            player = create_player(level, self.world)
        self.assertIn("FLOOR B1", player.status_text)
        self.assertIn("FLOOR: B1", "\n".join(player.debug_lines))
        peak = y
        for frame in range(240):
            player.update(1 / 120, InputState(jump=frame == 0))
            peak = max(peak, player.body.position.y)
            self.assertFalse(self.world.is_blocked(player.body.position, player.body.radius - 1e-5, player.body.height))
        self.assertGreater(peak, y + 0.8)
        self.assertAlmostEqual(peak + player.body.height, -self.layout.slab_thickness - 0.02, places=5)
        self.assertAlmostEqual(player.body.position.y, y, places=5)
        self.assertTrue(player.body.grounded)
