from dataclasses import replace
import unittest
from unittest.mock import patch

import glm
import pygame

from config import controls
from engine.collision.world3d import CollisionWorld3D
from engine.input.state import InputState
from engine.scene.box import Box
from engine.scene.camera import Camera
from engine.scene.interaction import Interaction
from engine.scene.level import Level
from engine.scene.object import ObjectState, SceneObject
from game.entities.player import create_player
from game.interactions import InteractionController


class InteractionTests(unittest.TestCase):
    def setUp(self):
        self.crate = Box((0, 1, -2), (1, 2, 1), interaction=Interaction("Crate", "The lid is shut."))
        self.camera = Camera((0, 1.6, 0), (0, 1.6, -1), 60, 0.1, 100)

    def controller(self, boxes):
        return InteractionController(tuple(boxes), reach=2.5, message_seconds=3, key_label="E")

    def test_ray_candidates_use_actual_segment_length_and_height(self):
        near = Box((0, 1, -5), (1, 2, 1))
        far = Box((0, 1, -20), (1, 2, 1))
        upstairs = Box((0, 7, -5), (1, 2, 1))
        controller = self.controller((near, far, upstairs))
        unit = controller._ray_colliders((0, 1, 0), (0, 0, -1), 5)
        non_unit = controller._ray_colliders((0, 1, 0), (0, 0, -5), 5)
        self.assertEqual(unit, non_unit)
        self.assertIn(0, non_unit)
        self.assertNotIn(1, non_unit)
        self.assertNotIn(2, non_unit)

    def test_aim_press_look_away_and_message_expiry(self):
        controller = self.controller((self.crate,))
        controller.update(0, self.camera)
        self.assertIs(controller.focused, self.crate)
        self.assertEqual(controller.text, "[E] Inspect - Crate")
        controller.update(0, self.camera, pressed=True)
        self.assertIn("The lid is shut.", controller.text)
        self.camera.target = self.camera.position + glm.vec3(1, 0, 0)
        controller.update(1, self.camera)
        self.assertIsNone(controller.focused)
        self.assertEqual(controller.text, "The lid is shut.")
        controller.update(2, self.camera)
        self.assertEqual(controller.text, "")

    def test_wall_or_noninteractive_box_blocks_action(self):
        wall = Box((0, 1.5, -1), (4, 3, 0.1))
        for boxes in ((wall, self.crate), (self.crate, wall)):
            controller = self.controller(boxes)
            controller.update(0, self.camera, pressed=True)
            self.assertIsNone(controller.focused)
            self.assertEqual(controller.text, "")

    def test_closest_object_and_surface_reach(self):
        far = replace(self.crate, position=(0, 1, -4), interaction=Interaction("Far crate", "Far"))
        controller = self.controller((far, self.crate))
        controller.update(0, self.camera, pressed=True)
        self.assertIs(controller.focused, self.crate)
        controller = self.controller((far,))
        controller.update(0, self.camera, pressed=True)
        self.assertIsNone(controller.focused)
        # Центр далеко, но передняя поверхность находится в пределах досягаемости.
        wide = replace(far, size=(1, 2, 4))
        controller = self.controller((wide,))
        controller.update(0, self.camera)
        self.assertIs(controller.focused, wide)

    def test_interaction_targets_are_visible_in_frame_without_center_aim(self):
        side_crate = replace(self.crate, position=(1, 1, -2))
        controller = self.controller((side_crate,))
        controller.update(0, self.camera, pressed=True)
        self.assertIs(controller.focused, side_crate)
        self.assertIn(side_crate.interaction.message, controller.text)

        wall = Box((0, 1.5, -1), (2, 3, 0.2))
        controller = self.controller((side_crate, wall))
        controller.update(0, self.camera, pressed=True)
        self.assertIsNone(controller.focused)

        offscreen_crate = replace(self.crate, position=(2.5, 1, -2))
        controller = self.controller((offscreen_crate,))
        controller.update(0, self.camera, pressed=True)
        self.assertIsNone(controller.focused)

    def test_player_uses_updated_view_and_decorations_block_interaction(self):
        level = Level((10, 10), 1, (self.crate,), (0, 1.6, 0), (0, 1.6, -1), ((80, 80, 80),) * 2)
        player = create_player(level, CollisionWorld3D((self.crate.collider,), level.floor_bounds))
        player.update(0, InputState(interact=True))
        self.assertIn(self.crate.interaction.message, player.aim_text)
        player.update(3, InputState(mouse_delta=(1500, 0), interact=True))
        self.assertEqual(player.aim_text, "")
        wall = Box((0, 1, -1), (2, 2, 0.1))
        level = replace(level, decorations=(wall,))
        player = create_player(level, CollisionWorld3D((self.crate.collider,)))
        player.update(0, InputState(interact=True))
        self.assertEqual(player.aim_text, "")

    def test_prompt_uses_configured_key(self):
        level = Level((10, 10), 1, (self.crate,), (0, 1.6, 0), (0, 1.6, -1), ((80, 80, 80),) * 2)
        with patch.object(controls, "INPUT_BINDINGS", replace(controls.INPUT_BINDINGS, interact=pygame.K_f)):
            player = create_player(level, CollisionWorld3D((self.crate.collider,)))
        player.update(0, InputState())
        self.assertIn("[F]", player.aim_text)

    def test_interaction_descriptions_require_readable_text(self):
        for values in (("", "Message"), ("Crate", " "), ("Crate", "Message", "")):
            with self.assertRaises(ValueError):
                Interaction(*values)

    def test_focus_losing_interaction_between_update_and_hud_render_is_safe(self):
        obj = SceneObject("drawer", {
            "default": ObjectState((self.crate,), interaction=Interaction("Drawer", "Opening", "Open", "open_door")),
            "open": ObjectState((replace(self.crate, position=(0, 1, -1.8)),),
                                interaction=Interaction("Drawer", "Closing", "Close", "close_door")),
            "hidden": ObjectState(),
        }, transition_seconds={"open": 0.8})
        controller = InteractionController((), reach=2.5, message_seconds=3, key_label="E", objects=(obj,))
        controller.update(0, self.camera)
        self.assertIs(controller.focused, obj)
        self.assertIn("Open", controller.text)
        obj.set_state("open")
        self.assertIsNone(obj.interaction)
        self.assertEqual(controller.text, "")
        self.assertEqual(controller._activate(obj), "")
        obj.update(1)
        self.assertIn("Close", controller.text)
        obj.set_state("hidden")
        self.assertEqual(controller.text, "")

    def test_visible_item_takes_priority_over_talking_to_nearby_companion(self):
        ally = SceneObject("ally", {"default": ObjectState(
            (Box((0, 1, -2), (0.5, 2, 0.5)),),
            interaction=Interaction("Companion", "Hello", "Talk", "talk"))})
        card = SceneObject("card", {"default": ObjectState(
            (Box((0.9, 1.1, -2), (0.3, 0.1, 0.3)),),
            interaction=Interaction("Card", "A note", "Read", "inspect"))})
        controller = InteractionController((), 2.5, 3, "E", objects=(ally, card))
        controller.update(0, self.camera, pressed=True)
        self.assertIs(controller.focused, card)
        self.assertIn("A note", controller.text)
        card.set_interaction(None)
        controller.update(0, self.camera)
        self.assertIs(controller.focused, ally)

    def test_companion_priority_does_not_allow_reading_items_through_walls(self):
        ally = SceneObject("ally", {"default": ObjectState(
            (Box((0, 1, -1.4), (0.5, 2, 0.5)),),
            interaction=Interaction("Companion", "Hello", "Talk", "talk"))})
        card = replace(self.crate, position=(0.9, 1.1, -2), size=(0.3, 0.1, 0.3))
        wall = Box((0.9, 1, -1.5), (1.0, 2, 0.1))
        controller = InteractionController((card, wall), 2.5, 3, "E", objects=(ally,))
        controller.update(0, self.camera)
        self.assertIs(controller.focused, ally)
