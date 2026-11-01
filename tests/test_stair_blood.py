import unittest

from game.levels import create_level
from game.levels.spiral import SpiralStair
from game.levels.stair_blood import stair_blood


class StairBloodTests(unittest.TestCase):
    def test_tread_droplets_rest_on_real_step_heights_and_ground_has_large_pools(self):
        stair = SpiralStair()
        stains = stair_blood(stair)
        heights = {round(stair.step_height(i), 6) for i in range(stair.steps * stair.flights)}
        horizontal = [b for b in stains if b.size[1] == 0.004]
        treads = [b for b in horizontal if b.size[0] < 0.2 and b.position[1] > 0.1]
        self.assertGreater(len(treads), 60)
        self.assertTrue(all(round(b.position[1] - 0.006, 6) in heights for b in treads))
        pools = [b for b in horizontal if b.position[1] < 0.01 and b.size[0] > 1]
        self.assertEqual(len(pools), 4)
        self.assertTrue(all(b.decal and b.color[0] > b.color[1] * 10 for b in stains))
        self.assertEqual(stains, stair_blood(stair))

    def test_blood_is_only_in_abandoned_world_and_never_adds_collision(self):
        abandoned, peaceful = create_level("start"), create_level("peaceful")
        stains = [b for b in abandoned.decorations if b.decal]
        self.assertTrue(stains)
        self.assertFalse(any(b.decal for b in peaceful.decorations))
        self.assertFalse(any(b.decal for b in abandoned.collision_boxes))
        self.assertEqual(len(abandoned.boxes), len(peaceful.boxes))
