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
from game.entities.player import create_player
from game.interactions import InteractionController
from game.levels import create_level


class InteractionTests(unittest.TestCase):
    def setUp(self):
        self.crate = Box((0, 1, -2), (1, 2, 1), interaction=Interaction("Crate", "The lid is shut."))
        self.camera = Camera((0, 1.6, 0), (0, 1.6, -1), 60, 0.1, 100)

    def controller(self, boxes):
        return InteractionController(tuple(boxes), reach=2.5, message_seconds=3, key_label="E")

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

    def test_player_uses_updated_view_and_decorations_block_interaction(self):
        level = Level((10, 10), 1, (self.crate,), (0, 1.6, 0), (0, 1.6, -1), ((80, 80, 80),) * 2)
        player = create_player(level, CollisionWorld3D((self.crate.collider,), level.floor_bounds))
        player.update(0, InputState(interact=True))
        self.assertIn(self.crate.interaction.message, player.aim_text)
        player.update(3, InputState(mouse_delta=(750, 0), interact=True))
        self.assertEqual(player.aim_text, "")
        wall = Box((0, 1, -1), (2, 2, 0.1))
        level = replace(level, decorations=(wall,))
        player = create_player(level, CollisionWorld3D((self.crate.collider,)))
        player.update(0, InputState(interact=True))
        self.assertEqual(player.aim_text, "")

    def test_actual_basement_has_three_explicit_interactions_with_individual_messages(self):
        level = create_level("maze")
        targets = tuple(b for b in level.boxes if b.interaction is not None)
        self.assertEqual(len(targets), 3)
        self.assertEqual(len({b.interaction.message for b in targets}), 3)
        controller = self.controller(level.boxes + level.decorations)
        for box in targets:
            x, y, z = box.position
            camera = Camera((x - 2, y, z), box.position, 60, 0.1, 100)
            controller.update(0, camera, pressed=True)
            self.assertIs(controller.focused, box)
            self.assertIn(box.interaction.message, controller.text)

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
