import itertools
import unittest

import glm

from config import settings
from engine.collision.world import CollisionWorld
from engine.scene.box import Box
from game.levels.demo import create_demo_level


class DemoLevelTests(unittest.TestCase):
    def test_model_and_collider_share_box_bounds(self):
        box = Box(position=(2, 3, -1), size=(4, 6, 8))
        corners = [
            box.model_matrix * glm.vec4(x, y, z, 1)
            for x, y, z in itertools.product((-1, 1), repeat=3)
        ]
        self.assertEqual(min(c.x for c in corners), box.footprint.min_x)
        self.assertEqual(max(c.x for c in corners), box.footprint.max_x)
        self.assertEqual(min(c.z for c in corners), box.footprint.min_z)
        self.assertEqual(max(c.z for c in corners), box.footprint.max_z)
        self.assertEqual(min(c.y for c in corners), 0)

    def test_demo_cube_stands_on_floor_and_spawn_is_free(self):
        level = create_demo_level()
        for box in level.boxes:
            self.assertAlmostEqual(box.position[1] - box.size[1] / 2, 0.0)
        world = CollisionWorld((box.footprint for box in level.boxes), level.floor_bounds)
        self.assertFalse(world.is_blocked(glm.vec3(settings.CAMERA_POSITION), settings.PLAYER_RADIUS))
        self.assertEqual(settings.CAMERA_POSITION[1], settings.PLAYER_EYE_HEIGHT)
