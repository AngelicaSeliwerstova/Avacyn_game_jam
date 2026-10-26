import os
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree

import glm

from config import settings
from engine.collision.world import CollisionWorld
from engine.controllers.first_person import FirstPersonController
from engine.scene.camera import Camera
from engine.scene.tiled_level import load_tiled_level
from game.levels import create_level


MAP_PATH = Path(__file__).resolve().parents[1] / "resources" / "levels" / "corridor.tmx"


class CorridorTests(unittest.TestCase):
    def setUp(self):
        self.level = create_level("corridor")
        self.world = CollisionWorld(
            (box.footprint for box in self.level.boxes), self.level.floor_bounds,
        )

    def test_start_is_clear_and_looks_down_corridor(self):
        position = glm.vec3(self.level.spawn_position)
        direction = glm.vec3(self.level.spawn_target) - position
        self.assertFalse(self.world.is_blocked(position, settings.PLAYER_RADIUS))
        self.assertAlmostEqual(position.y, settings.PLAYER_EYE_HEIGHT, places=5)
        self.assertAlmostEqual(direction.x, 0, places=5)
        self.assertAlmostEqual(direction.y, 0, places=5)
        self.assertLess(direction.z, 0)

    def test_can_walk_turn_and_return_at_different_frame_rates(self):
        for fps in (30, 60, 120):
            with self.subTest(fps=fps):
                camera = Camera(self.level.spawn_position, self.level.spawn_target, 60, 0.1, 100)
                controller = FirstPersonController(
                    camera, 2.5, 0.12, 80, 0.1, 0.25, 0.1, self.world,
                )
                for turn, expected in (
                    (0, (-6, 1.6, -6)),
                    (750, (7, 1.6, -6)),
                    (1500, (-6, 1.6, -6)),
                    (-750, (-6, 1.6, 7)),
                ):
                    controller.update(0, mouse_delta=(turn, 0))
                    for _ in range(round(fps * 5.2)):
                        controller.update(1 / fps, forward_axis=1)
                        self.assertFalse(self.world.is_blocked(camera.position, 0.25 - 1e-5))
                    self.assertLess(glm.length(camera.position - glm.vec3(expected)), 0.002)

    def test_inner_wall_blocks_movement_at_tile_joints(self):
        for z in (-2, 0, 2, 4, 6):
            with self.subTest(z=z):
                position = self.world.move(glm.vec3(-6, 1.6, z), glm.vec3(20, 0, 0), 0.25, 0.1)
                self.assertAlmostEqual(position.x, -4.25, places=5)
                self.assertAlmostEqual(position.z, z, places=5)

    def test_closed_ends_block_long_movements(self):
        for start, movement, expected in (
            ((-6, 1.6, 7), (0, 0, 100), (-6, 1.6, 7.75)),
            ((-6, 1.6, -6), (0, 0, -100), (-6, 1.6, -7.75)),
            ((7, 1.6, -6), (100, 0, 0), (7.75, 1.6, -6)),
        ):
            with self.subTest(start=start):
                position = self.world.move(glm.vec3(start), glm.vec3(movement), 0.25, 0.1)
                self.assertLess(glm.length(position - glm.vec3(expected)), 1e-5)

    def test_walls_stand_on_floor_and_use_world_units(self):
        self.assertEqual(self.level.floor_size, (20.0, 20.0))
        for box in self.level.boxes:
            self.assertEqual(box.size, (2.0, 2.8, 2.0))
            self.assertAlmostEqual(box.position[1] - box.size[1] / 2, 0)

    def test_map_loads_from_another_working_directory(self):
        original_directory = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                level = create_level("corridor")
            finally:
                os.chdir(original_directory)
        self.assertEqual(level, self.level)

    def test_spawn_inside_wall_is_rejected(self):
        tree = ElementTree.parse(MAP_PATH)
        tree.getroot().find("objectgroup/object").set("x", "16")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.tmx"
            tree.write(path, encoding="utf-8", xml_declaration=True)
            with self.assertRaisesRegex(ValueError, "wall tile"):
                load_tiled_level(path, eye_height=1.6, floor_colors=settings.FLOOR_COLORS)
