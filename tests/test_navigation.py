import math
import unittest

from engine.navigation.graph import NavigationGraph
from engine.navigation.traversal import NavigationTraversal, TraversalProfile
from engine.scene.box import Box
from engine.scene.object import ObjectState, SceneObject


class NavigationTests(unittest.TestCase):
    def traversal(self, boxes=(), objects=()):
        return NavigationTraversal((b.collider for b in boxes), objects, None,
                                   TraversalProfile(0.25, 1.8, 0.3))

    def test_can_leave_free_space_near_axis_aligned_and_rotated_corners(self):
        for yaw in (0, 45, 90):
            for dynamic in (False, True):
                with self.subTest(yaw=yaw, dynamic=dynamic):
                    box = Box((0, 1, 0), (2, 2, 2), yaw_degrees=yaw)
                    obj = SceneObject("door", {"open": ObjectState((box,))}, initial="open")
                    nav = self.traversal(objects=(obj,)) if dynamic else self.traversal((box,))
                    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
                    def point(x, z):
                        return (c * x + s * z, 0, -s * x + c * z)
                    a, b = point(1.2, 1.2), point(2, 2)
                    self.assertFalse(box.footprint.intersects_circle(a[0], a[2], nav.radius))
                    self.assertTrue(nav.can_walk(a, b))
                    self.assertTrue(nav.can_walk(b, a))

    def test_sweep_catches_rounded_corner_between_clear_endpoints(self):
        box = Box((0, 1, 0), (2, 2, 2))
        a, b = (1.1, 0, 1.25), (1.25, 0, 1.1)
        for p in (a, b):
            self.assertFalse(box.footprint.intersects_circle(p[0], p[2], 0.25))
        self.assertFalse(self.traversal((box,)).can_walk(a, b))

    def test_sweep_catches_thin_wall_between_clear_endpoints(self):
        nav = self.traversal((Box((0, 1, 0), (0.01, 2, 4)),))
        self.assertFalse(nav.can_walk((-2, 0, 0), (2, 0, 0)))
        self.assertTrue(nav.can_walk((-2, 3, 0), (2, 3, 0)))

    def test_connections_consider_reachable_nodes_beyond_twelve_nearest(self):
        wall = Box((0, 1, 0), (0.1, 2, 4))
        blocked = tuple((0.4, 0, i * 0.02) for i in range(12))
        goal = (-2, 0, 0)
        graph = NavigationGraph((*blocked, goal), (), connection_distance=3)
        result = graph.find_path((-0.4, 0, 0), goal, self.traversal((wall,)))
        self.assertTrue(result.complete)
        self.assertEqual(result.points[-1], goal)
