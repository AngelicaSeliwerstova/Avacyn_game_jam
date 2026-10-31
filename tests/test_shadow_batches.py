import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import glm

from engine.rendering.lighting import LevelLighting
from engine.scene.box import Box
from engine.scene.lighting import Lighting, PointLight


class ShadowBatchTests(unittest.TestCase):
    def lighting(self):
        lighting = LevelLighting.__new__(LevelLighting)
        lighting._context = Mock()
        lighting._framebuffer = Mock()
        lighting._cube = Mock()
        lighting._program = {"m_light": Mock()}
        lighting._instance_buffer = Mock(size=100000)
        lighting._atlas_columns = 8
        lighting._level = SimpleNamespace(lighting=Lighting((0.2, 0.2, 0.2), (
            PointLight((0, 3, 0), radius=5), PointLight((30, 3, 0), radius=5))))
        lighting._static_nearby = ((glm.mat4(1).to_bytes(),) * 100, ())
        lighting._object_boxes = ()
        lighting._extra_shadow_boxes = ()
        return lighting

    def test_many_shadow_casters_use_one_instanced_draw_per_face(self):
        lighting = self.lighting()
        box = Box((0, 1, 1), (1, 2, 1), yaw_degrees=35)
        lighting._render_lights((0,), 128, (box,))
        self.assertEqual(lighting._cube.render.call_count, 6)
        for call in lighting._cube.render.call_args_list:
            self.assertEqual(call.kwargs, {"instances": 101})
        lighting._instance_buffer.write.assert_called_once()
        self.assertEqual(len(lighting._instance_buffer.write.call_args.args[0]), 101 * 64)
        self.assertEqual(lighting._framebuffer.clear.call_count, 6)

    def test_empty_light_still_clears_old_shadows_without_drawing(self):
        lighting = self.lighting()
        lighting._render_lights((1,), 128, ())
        lighting._cube.render.assert_not_called()
        self.assertEqual(lighting._framebuffer.clear.call_count, 6)

    def test_door_motion_updates_only_nearby_lights_and_preserves_creator_casters(self):
        lighting = self.lighting()
        old = Box((0, 1, 0), (1, 2, 0.2))
        moved = old.rotated_around((-0.5, 0, 0), 45)
        extra = Box((2, 1, 0), (1, 2, 1))
        lighting._object_boxes = (old,)
        lighting._extra_shadow_boxes = (extra,)
        lighting._render_lights = Mock()
        lighting.sync_objects((moved,))
        args = lighting._render_lights.call_args.args
        self.assertEqual(args[0], [0])
        self.assertEqual(args[2], (moved, extra))
        lighting._render_lights.reset_mock()
        lighting.sync_objects((moved,))
        lighting._render_lights.assert_not_called()
