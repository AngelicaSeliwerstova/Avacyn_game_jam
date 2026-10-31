import unittest

import glm

from game.campaign import Campaign
from game.levels import create_level
from test_hospital import walk


class WorldTransitionTests(unittest.TestCase):
    def test_peaceful_world_copies_first_floor_rooms(self):
        peaceful, hospital = create_level("peaceful"), create_level("start")
        self.assertEqual(peaceful.floor_size, hospital.floor_size)
        self.assertEqual(peaceful.floor_heights, (0,))
        self.assertEqual(hospital.floor_heights, (0, 4.8, 9.6))
        first_floor = {o.name for o in hospital.objects if not o.name.startswith(("f2_", "f3_"))}
        self.assertEqual(first_floor, {o.name for o in peaceful.objects if o.name != "doctor_room_transition"})
        self.assertEqual(peaceful.floor_material, "linoleum_blue_gray")
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
        goal = scene.session.goals[0]
        for position in ((-17, 0, -4.5), (-17, 0, -6), (-17, 0, -8)):
            self.assertFalse(goal.reached(position, scene.player.inventory))
