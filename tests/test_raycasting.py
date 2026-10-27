import unittest

from engine.collision.aabb import AABB
from engine.collision.aabb3d import AABB3D
from engine.raycasting.aabb import cast_ray


class RaycastingTests(unittest.TestCase):
    def setUp(self):
        self.box = AABB3D(AABB(-1, -1, 1, 1), -1, 1)

    def test_all_six_faces_with_nonunit_direction_report_world_distance(self):
        for axis in range(3):
            for sign in (-1, 1):
                origin, direction, point = [0.0] * 3, [0.0] * 3, [0.0] * 3
                origin[axis], direction[axis], point[axis] = 3 * sign, -10 * sign, sign
                hit = cast_ray(origin, direction, (self.box,), 2)
                self.assertIsNotNone(hit)
                self.assertAlmostEqual(hit.distance, 2)
                self.assertEqual(hit.position, tuple(point))

    def test_parallel_miss_behind_camera_and_surface_outside_reach(self):
        for origin, direction, reach in (
            ((2, 0, 3), (0, 0, -1), 10),
            ((0, 0, 3), (0, 0, 1), 10),
            ((0, 0, 3), (0, 0, -1), 1.99),
        ):
            self.assertIsNone(cast_ray(origin, direction, (self.box,), reach))

    def test_inside_and_on_edge_are_hits(self):
        self.assertEqual(cast_ray((0, 0, 0), (1, 0, 0), (self.box,), 0).distance, 0)
        hit = cast_ray((1, 1, 3), (0, 0, -1), (self.box,), 2)
        self.assertEqual(hit.position, (1, 1, 1))

    def test_nearest_hit_is_independent_of_iteration_order(self):
        far = AABB3D(AABB(-1, -5, 1, -3), -1, 1)
        for boxes, expected in (((far, self.box), 1), ((self.box, far), 0)):
            hit = cast_ray((0, 0, 3), (0, 0, -1), boxes, 20)
            self.assertEqual(hit.index, expected)
            self.assertEqual(hit.distance, 2)
        self.assertIsNone(cast_ray((0, 0, 3), (0, 0, -1), (), 20))

    def test_invalid_rays_are_rejected(self):
        for origin, direction, reach in (
            ((0, 0, 0), (0, 0, 0), 2),
            ((0, float("nan"), 0), (1, 0, 0), 2),
            ((0, 0, 0), (float("inf"), 0, 0), 2),
            ((0, 0, 0), (1, 0, 0), -1),
            ((0, 0, 0), (1, 0, 0), float("inf")),
            ((0, 0), (1, 0, 0), 2),
        ):
            with self.assertRaises(ValueError):
                cast_ray(origin, direction, (self.box,), reach)
