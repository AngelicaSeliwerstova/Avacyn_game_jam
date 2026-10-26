from collections import deque
from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest

import glm

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.input.state import InputState
from engine.physics.character import CharacterBody
from game.entities.player import create_player
from game.levels import create_level
from game.levels.maze import maze_layout_path
from game.levels.maze_layout import load_maze_layout


def make_body(world, position, jump_height=None):
    return CharacterBody(position, world, radius=settings.PLAYER_RADIUS, height=settings.PLAYER_HEIGHT,
                         step_height=settings.PLAYER_STEP_HEIGHT, gravity=settings.GRAVITY,
                         collision_max_step=settings.COLLISION_MAX_STEP, physics_step=settings.PHYSICS_STEP,
                         camera_smoothing=settings.STAIR_CAMERA_SMOOTHING,
                         jump_height=settings.JUMP_HEIGHT if jump_height is None else jump_height)


def walk(body, points, fps):
    for target in points:
        for _ in range(fps * 30):
            delta = glm.vec3(target[0] - body.position.x, 0, target[2] - body.position.z)
            distance = glm.length(delta)
            if distance < 0.002:
                break
            body.update(1 / fps, delta / distance * min(settings.SPRINT_SPEED, distance * fps))
            if body.world.is_blocked(body.position, body.radius - 1e-5, body.height):
                raise AssertionError(f"Body overlaps maze at {body.position}")
        else:
            raise AssertionError(f"Cannot reach {target} from {body.position}")
        if abs(body.position.y - target[1]) > 0.01:
            raise AssertionError(f"Wrong floor at {target}: {body.position}")


class MazeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = load_maze_layout(maze_layout_path())
        cls.level = create_level("maze")
        cls.world = CollisionWorld3D((box.collider for box in cls.level.boxes), cls.level.floor_bounds)

    def test_all_open_cells_on_both_floors_are_connected(self):
        layout = self.layout
        nodes = {(floor, row, column) for floor, rows in enumerate(layout.floors)
                 for row, cells in enumerate(rows) for column, cell in enumerate(cells) if cell == "."}
        visited = {layout.spawn}
        queue = deque(visited)
        while queue:
            for neighbor in layout.neighbors(queue.popleft()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        self.assertEqual(nodes, visited)
        self.assertGreater(len(nodes), 400)
        branches = sum(len(tuple(layout.neighbors(node))) >= 3 for node in nodes)
        dead_ends = sum(len(tuple(layout.neighbors(node))) == 1 for node in nodes)
        self.assertGreater(branches, 25)
        self.assertGreater(dead_ends, 10)
        self.assertNotEqual(layout.floors[0], layout.floors[1])
        for node in nodes:
            position = glm.vec3(layout.position(node))
            self.assertFalse(self.world.is_blocked(position, settings.PLAYER_RADIUS, settings.PLAYER_HEIGHT), node)
            self.assertAlmostEqual(self.world.support_height(position, settings.PLAYER_RADIUS, position.y),
                                   node[0] * layout.floor_height, places=5)

    def test_exit_is_reachable_with_actual_physics_at_30_60_120_fps(self):
        layout = self.layout
        points = layout.walk_points(layout.path(layout.spawn, layout.exit)) + (layout.goal_position,)
        for fps in (30, 60, 120):
            with self.subTest(fps=fps):
                body = make_body(self.world, points[0])
                walk(body, points[1:], fps)
                self.assertLess(glm.length(body.position - glm.vec3(layout.goal_position)), 0.005)
                self.assertTrue(body.grounded)

    def test_both_staircases_work_in_both_directions(self):
        for link in self.layout.stairs:
            points = self.layout.stair_points(link)
            for fps in (30, 60, 120):
                with self.subTest(stair=link.name, fps=fps):
                    body = make_body(self.world, points[0])
                    walk(body, points[1:], fps)
                    self.assertAlmostEqual(body.position.y, self.layout.floor_height, places=5)
                    walk(body, tuple(reversed(points))[1:], fps)
                    self.assertAlmostEqual(body.position.y, 0.0, places=5)

    def test_floor_slab_is_solid_and_stops_jump_from_below(self):
        x, _, z = self.layout.position(self.layout.spawn)
        body = make_body(self.world, (x, 0, z), jump_height=12)
        peak = 0
        for frame in range(240):
            body.update(1 / 120, glm.vec3(0), jump=frame == 0)
            peak = max(peak, body.position.y)
            self.assertFalse(self.world.is_blocked(body.position, body.radius - 1e-5, body.height))
        self.assertAlmostEqual(peak, self.layout.wall_height - body.height, places=5)
        self.assertAlmostEqual(body.position.y, 0, places=5)

    def test_only_authored_stair_doors_and_exit_open_the_perimeter(self):
        allowed = {node for link in self.layout.stairs for node in self.layout.stair_nodes(link)}
        allowed.add(self.layout.exit)
        for floor, rows in enumerate(self.layout.floors):
            for row, cells in enumerate(rows):
                for column, cell in enumerate(cells):
                    if cell == "." and (row in (0, len(rows) - 1) or column in (0, len(cells) - 1)):
                        self.assertIn((floor, row, column), allowed)

    def test_goal_status_requires_upper_floor_and_remains_after_leaving(self):
        x, y, z = self.layout.goal_position
        below = replace(self.level, spawn_position=(x, settings.PLAYER_EYE_HEIGHT, z),
                        spawn_target=(x, settings.PLAYER_EYE_HEIGHT, z + 1))
        player = create_player(below, self.world)
        player.update(0, InputState())
        self.assertNotIn("EXIT FOUND", player.status_text)
        above = replace(self.level, spawn_position=(x, y + settings.PLAYER_EYE_HEIGHT, z),
                        spawn_target=(x, y + settings.PLAYER_EYE_HEIGHT, z + 1))
        player = create_player(above, self.world)
        player.update(0, InputState())
        self.assertIn("EXIT FOUND", player.status_text)
        for _ in range(30):
            player.update(1 / 60, InputState(forward=1))
        self.assertIn("EXIT FOUND", player.status_text)

    def test_level_loads_from_another_directory_and_disables_indoor_snow(self):
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                level = create_level("maze")
            finally:
                os.chdir(original)
        self.assertEqual(level, self.level)
        self.assertFalse(level.snow_enabled)
        self.assertEqual(level.floor_heights, (0, 3.6))
        self.assertEqual(level.floor_size, (81, 75))


if __name__ == "__main__":
    unittest.main()
