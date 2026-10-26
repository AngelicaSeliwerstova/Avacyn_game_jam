from array import array
from dataclasses import replace
import unittest

from engine.rendering.light_grid import build_light_grid
from engine.rendering.visibility import ViewFrustum
from engine.scene.camera import Camera
from engine.scene.level import Level
from engine.scene.lighting import Lighting, PointLight


class VisibilityTests(unittest.TestCase):
    def test_frustum_keeps_crossing_near_plane_and_rejects_behind_camera_and_far_objects(self):
        camera = Camera((0, 0, 0), (0, 0, -1), 60, 0.1, 10)
        frustum = ViewFrustum(camera.projection_matrix(4 / 3) * camera.view_matrix)
        self.assertTrue(frustum.intersects((0, 0, -3), (0.5, 0.5, 0.5)))
        self.assertTrue(frustum.intersects((0, 0, 0), (1, 1, 1)))
        self.assertFalse(frustum.intersects((0, 0, 3), (0.5, 0.5, 0.5)))
        self.assertFalse(frustum.intersects((0, 0, -12), (0.5, 0.5, 0.5)))
        self.assertFalse(frustum.intersects((10, 0, -3), (0.5, 0.5, 0.5)))
        self.assertTrue(frustum.intersects((0, 0, -20), (100, 100, 100)))

    def test_grid_preserves_all_overlapping_lights_in_order_without_nearest_n_truncation(self):
        lights = tuple(PointLight((0, 3, 0), radius=8) for _ in range(30)) + (PointLight((100, 3, 0)),)
        level = Level((20, 20), 1, (), (0, 1.6, 0), (0, 1.6, -1), ((80, 80, 80),) * 2,
                      lighting=Lighting((0.1, 0.1, 0.1), lights))
        grid = build_light_grid(level, 4, 16384)
        self.assertEqual(grid.max_lights, 30)
        data = array("i", grid.indices)
        row_width = grid.texture_size[0]
        cells_with_lights = 0
        for offset in range(0, len(data), row_width):
            count = data[offset]
            if count:
                cells_with_lights += 1
                self.assertEqual(tuple(data[offset + 1:offset + count + 1]), tuple(range(30)))
        self.assertGreater(cells_with_lights, 0)
        self.assertIsNone(build_light_grid(level, 0.001, 100))
        self.assertIsNone(build_light_grid(replace(level, lighting=None), 4, 16384))
