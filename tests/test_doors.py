import unittest

import glm

from engine.collision.world3d import CollisionWorld3D
from engine.scene.camera import Camera
from engine.scene.level import Level
from game.entities.player import create_player
from game.interactions import InteractionController
from game.levels.objects import build_objects


class DoorTests(unittest.TestCase):
    def make_door(self, **options):
        objects = build_objects([{"id": "door", "type": "door", "position": [0, 0, 0], **options}])
        door = objects[-1]
        controller = InteractionController((), 3, 2, "E", objects=objects)
        return objects, door, controller

    def test_repeated_open_close_cycles_restore_geometry_and_collision(self):
        objects, door, controller = self.make_door()
        world = CollisionWorld3D((), objects=objects)
        for _ in range(3):
            self.assertTrue(world.is_blocked(glm.vec3(0, 0, 0), 0.25, 1.8))
            controller._activate(door)
            self.assertIsNone(door.interaction)
            door.update(1)
            self.assertEqual(door.interaction.command, "close_door")
            self.assertFalse(world.is_blocked(glm.vec3(0, 0, 0), 0.25, 1.8))
            controller._activate(door)
            self.assertIsNone(door.interaction)
            door.update(1)
            self.assertEqual(door.current_state, door.states["default"])
            self.assertEqual(door.interaction.command, "open_door")

    def test_collision_index_rebuilds_when_door_changes_but_not_for_same_creator_boxes(self):
        objects, door, _ = self.make_door()
        world = CollisionWorld3D((), objects=objects)
        closed_colliders = world.colliders
        world.set_creator_colliders(())
        self.assertIs(world.colliders, closed_colliders)

        door.set_state("open")
        door.update(1)
        self.assertFalse(world.is_blocked(glm.vec3(0, 0, 0), 0.25, 1.8))

    def test_locked_door_still_needs_key_and_can_be_closed_then_reopened(self):
        _, door, controller = self.make_door(key_id="office")
        self.assertIn("Дверь заперта", controller._activate(door))
        self.assertIn("locked:door", controller.events)
        self.assertEqual(door.current_state, door.states["default"])
        controller.inventory.add_key("office", "Office key")
        controller._activate(door)
        door.update(1)
        controller._activate(door)
        door.update(1)
        self.assertEqual(door.interaction.command, "unlock_door")
        self.assertTrue(controller.inventory.has_key("office"))
        controller._activate(door)
        door.update(1)
        self.assertEqual(door.current_state, door.states["open"])

    def test_prompt_and_same_interact_key_switch_between_open_and_close(self):
        _, door, controller = self.make_door()
        camera = Camera((0, 1.6, 1.5), (0, 1.3, 0), 70, 0.1, 100)
        controller.update(0, camera)
        self.assertIn("[E] Открыть", controller.text)
        controller.update(0, camera, pressed=True)
        door.update(1)
        panel = door.boxes[0]
        camera.position = glm.vec3(panel.position) + glm.vec3(1.5, 0, 0)
        camera.target = glm.vec3(panel.position)
        controller.update(0, camera)
        self.assertIs(controller.focused, door)
        self.assertIn("[E] Закрыть", controller.text)
        controller.update(0, camera, pressed=True)
        door.update(1)
        self.assertEqual(door.state_name, "default")

    def test_close_animation_stops_before_player_and_resumes_after_they_move(self):
        objects, door, controller = self.make_door()
        door.set_state("open")
        door.update(1)
        level = Level((10, 10), 1, (), (0, 1.6, 0.08), (0, 1.6, -1), ((80, 80, 80),) * 2,
                      objects=objects)
        world = CollisionWorld3D((), level.floor_bounds, objects=objects)
        player = create_player(level, world)
        controller._activate(door)
        door.update(10)
        self.assertNotEqual(door.current_state, door.states["default"])
        self.assertFalse(world.is_blocked(player.body.position, player.body.radius, player.body.height))
        player.body.update(0.75, glm.vec3(0, 0, 3))
        door.update(1)
        self.assertEqual(door.current_state, door.states["default"])
        self.assertFalse(world.is_blocked(player.body.position, player.body.radius, player.body.height))

    def test_custom_close_duration(self):
        _, door, controller = self.make_door(open_seconds=0.2, close_seconds=2)
        controller._activate(door)
        door.update(0.2)
        controller._activate(door)
        door.update(0.2)
        self.assertNotEqual(door.current_state, door.states["default"])
        door.update(1.8)
        self.assertEqual(door.current_state, door.states["default"])


if __name__ == "__main__":
    unittest.main()
