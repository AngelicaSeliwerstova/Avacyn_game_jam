import itertools
import unittest

import glm

from engine.scene.box import Box


class BoxGeometryTests(unittest.TestCase):
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
