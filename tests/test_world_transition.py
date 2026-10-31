import unittest

import glm

from game.campaign import Campaign
from game.levels import create_level
from test_hospital import make_body, walk
from game.levels.spiral import SpiralStair


class WorldTransitionTests(unittest.TestCase):
    def test_stair_barrier_is_invisible_blocks_movement_and_warns_on_approach(self):
        scene = Campaign().load_level("peaceful")
        level, player = scene.level, scene.player
        self.assertEqual(len(level.invisible_barriers), 1)
        barrier = level.invisible_barriers[0]
        self.assertNotIn(barrier, level.boxes + level.decorations + level.all_object_boxes)
        self.assertIn(barrier.collider, player.body.world.colliders)
        stair = SpiralStair()
        radius = (stair.inner_radius + stair.outer_radius) / 2
        player.body = make_body(player.body.world, stair.point(47, radius))
        self.assertEqual(player.aim_text, "Пока туда нельзя.")
        # Walk towards the first rising steps: the barrier cannot be stepped over.
        for _ in range(90):
            player.body.update(1 / 60, glm.vec3(1.5, 0, -2.6))
        self.assertGreater(player.body.position.z, barrier.position[2] - 0.5)
        self.assertAlmostEqual(player.body.position.y, 0)
        player.body = make_body(player.body.world, (-18.5, 0, -3.5))
        self.assertNotIn("Пока туда нельзя", player.aim_text)
        self.assertEqual(create_level("start").invisible_barriers, ())

    def test_stair_lobby_connects_to_the_open_south_hall_in_both_worlds(self):
        for name in ("peaceful", "start"):
            scene = Campaign().load_level(name)
            for obj in scene.level.objects:
                if "open" in obj.states:
                    obj.set_state("open")
                    obj.update(1)
            for height in scene.level.floor_heights:
                scene.player.body = make_body(scene.player.body.world, (3.5, height, 10.5))
                points = ((-8, height, 10.5), (-12.95, height, 8.6)) if height == 0 else (
                    (-8, height, 10.5), (-8, height, 6.9), (-12.2, height, 6.9))
                walk(self, scene.player.body, points)
                self.assertAlmostEqual(scene.player.body.position.y, height, places=4)

    def test_worlds_share_all_three_floors_and_furniture_geometry(self):
        peaceful, hospital = create_level("peaceful"), create_level("start")
        self.assertEqual(peaceful.floor_size, (60, 48))
        self.assertEqual(hospital.floor_size, (60, 48))
        self.assertEqual(peaceful.floor_heights, (0, 4.8, 9.6))
        self.assertEqual(hospital.floor_heights, (0, 4.8, 9.6))
        self.assertEqual({o.name for o in hospital.objects}, {o.name for o in peaceful.objects})
        geometry = lambda boxes: tuple((b.position, b.size, b.yaw_degrees) for b in boxes)
        self.assertEqual(geometry(hospital.boxes), geometry(peaceful.boxes))
        # Creator edits are per-map overlays; compare the shared authored building.
        self.assertEqual(geometry(b for b in hospital.decorations if b not in hospital.creator_objects),
                         geometry(b for b in peaceful.decorations if b not in peaceful.creator_objects))
        self.assertEqual(geometry(hospital.all_object_boxes), geometry(peaceful.all_object_boxes))
        self.assertNotEqual(tuple(b.material for b in hospital.boxes),
                            tuple(b.material for b in peaceful.boxes))
        self.assertEqual(peaceful.floor_material, "terrazzo_gray")
        self.assertEqual(hospital.floor_material, "floor_tile_dirty")
        self.assertNotEqual(peaceful.camera_save_path, hospital.camera_save_path)

    def test_far_office_trigger_is_reachable_and_transfers_inventory_and_effects(self):
        campaign = Campaign()
        peaceful = campaign.load_level("peaceful")
        self.assertIsNone(peaceful.fog)
        self.assertIsNone(peaceful.postprocess)
        peaceful.session.update(0)
        self.assertIsNone(peaceful.session.next_level)
        for obj in peaceful.level.objects:
            if "open" in obj.states:
                obj.set_state("open")
                obj.update(1)
        body = peaceful.player.body
        walk(self, body, ((3.5, 0, 12.2), (3.5, 0, -4.5), (-17, 0, -4.5),
                         (-17, 0, -8.1), (-15.9, 0, -8.6), (-15.9, 0, -10.9)))
        peaceful.session.update(0)
        self.assertIsNone(peaceful.session.next_level)
        speaker = next(o for o in peaceful.level.objects if o.name == "hospital_companion")
        peaceful.player._interactions._activate(speaker)
        peaceful.session.update(0)
        self.assertIsNotNone(peaceful.session.dialog)
        for _ in speaker.entity.dialogue:
            peaceful.session.handle_action("dialogue_next")
        self.assertEqual(peaceful.session.next_level, "start")
        peaceful.player.inventory.add_key("story", "Сюжетный ключ")
        hospital = campaign.load_level(peaceful.session.next_level)
        self.assertIs(peaceful.player.inventory, hospital.player.inventory)
        self.assertTrue(hospital.player.inventory.has_key("story"))
        self.assertIn("peaceful", campaign.progress.completed_levels)
        self.assertIsNotNone(hospital.fog)
        self.assertIsNotNone(hospital.postprocess)
        self.assertLess(glm.distance(hospital.player.body.position, glm.vec3(-16.1, 0, -11)), 0.01)
        hospital.session.update(0)
        self.assertIsNone(hospital.session.next_level)

    def test_portal_does_not_fire_from_corridor_or_doorway(self):
        scene = Campaign().load_level("peaceful")
        door = next(obj for obj in scene.level.objects if obj.name == "office_0")
        door.set_state("open")
        door.update(1)
        self.assertEqual(scene.session.goals, ())
        for position in ((-17, 0, -4.5), (-17, 0, -6), (-17, 0, -8)):
            scene.player.body = make_body(scene.player.body.world, position)
            scene.session.update(0)
            self.assertIsNone(scene.session.next_level)
            self.assertIsNone(scene.session.dialog)
