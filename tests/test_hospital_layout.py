"""Physical doorway checks across all three hospital floors."""

import math
import unittest

import glm

from engine.collision.world3d import CollisionWorld3D
from game.levels import create_level
from game.levels.hospital import OFFICE_DOORS, ROOM_NAMES
from game.campaign import Campaign
from test_hospital import make_body, walk


class HospitalLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.level = create_level("start")
        cls.doors = tuple(obj for obj in cls.level.objects if "open" in obj.states)
        for door in cls.doors:
            door.set_state("open")
            door.update(1)
        cls.world = CollisionWorld3D(
            (box.collider for box in cls.level.collision_boxes), cls.level.floor_bounds,
            objects=tuple(obj for obj in cls.level.objects if obj.entity is None),
        )

    def test_every_open_door_can_be_crossed_in_both_directions(self):
        for door in self.doors:
            with self.subTest(door=door.name):
                panel = door.states["default"].boxes[0]
                height = min(self.level.floor_heights,
                             key=lambda y: abs(y - (panel.position[1] - panel.size[1] / 2)))
                center = glm.vec3(panel.position[0], height, panel.position[2])
                normal = glm.vec3(0, 0, 0.55) if panel.size[0] > panel.size[2] else glm.vec3(0.55, 0, 0)
                a, b = tuple(center - normal), tuple(center + normal)
                body = make_body(self.world, a)
                walk(self, body, (b, a), fps=30)

    def test_reference_has_six_north_rooms_and_two_security_entrances(self):
        self.assertEqual(ROOM_NAMES, ("Кабинет врача", "Процедурная", "Смотровая",
                                      "Склад", "Палата 01", "Палата 02"))
        ground = {obj.name: obj for obj in self.doors
                  if not obj.name.startswith(("f2_", "f3_"))}
        self.assertEqual(set(ground), {*(f"office_{i}" for i in range(6)),
                                      "security_0", "security_hall_0"})
        for index, x in enumerate(OFFICE_DOORS):
            panel = ground[f"office_{index}"].states["default"].boxes[0]
            self.assertEqual((panel.position[0], panel.position[2]), (x, -6))
        for name, z in (("security_0", 0), ("security_hall_0", 8)):
            panel = ground[name].states["default"].boxes[0]
            self.assertEqual((panel.position[0], panel.position[2]), (-3, z))

    def test_ground_floor_wards_allow_access_to_both_sides_of_privacy_screens(self):
        for x in (11, 18):
            with self.subTest(room=x):
                body = make_body(self.world, (x, 0, -8))
                walk(self, body, ((x - 0.5, 0, -9), (x - 0.5, 0, -12.5),
                                 (x - 0.5, 0, -9), (x + 0.5, 0, -9),
                                 (x + 0.5, 0, -12.5), (x + 0.5, 0, -9),
                                 (x, 0, -8)), fps=30)

    def test_surgical_rooms_join_envelope_and_cross_hall_stays_open(self):
        # Partitions must reach the envelope, closing the old perimeter alleys.
        for x, z in ((-20, -23), (20, -23), (14, 23)):
            with self.subTest(partition=(x, z)):
                self.assertTrue(self.world.is_blocked(glm.vec3(x, 4.8, z), 0.25, 1.8))
        # The former detached cross-wall and its lobby returns are gone.
        for x, z in ((-6, -4), (6, -6), (18, -6), (26, -6), (-6, 18)):
            with self.subTest(hall=(x, z)):
                body = make_body(self.world, (x - 0.6, 4.8, z))
                walk(self, body, ((x + 0.6, 4.8, z),), fps=30)

    def test_opening_animation_does_not_sweep_through_static_walls_or_furniture(self):
        world = CollisionWorld3D((box.collider for box in self.level.collision_boxes),
                                 self.level.floor_bounds)
        for door in self.doors:
            with self.subTest(door=door.name):
                for frame in range(1, 13):
                    state = door._interpolate(door.states["default"], door.states["open"], frame / 12)
                    panel = state.boxes[0]
                    height = min(self.level.floor_heights,
                                 key=lambda y: abs(y - (panel.position[1] - panel.size[1] / 2)))
                    c, s = math.cos(math.radians(panel.yaw_degrees)), math.sin(math.radians(panel.yaw_degrees))
                    for sample in range(17):
                        along = (sample / 16 - 0.5) * (max(panel.size[0], panel.size[2]) - 0.04)
                        dx, dz = (along, 0) if panel.size[0] > panel.size[2] else (0, along)
                        position = glm.vec3(panel.position[0] + c * dx + s * dz, height + 0.02,
                                            panel.position[2] - s * dx + c * dz)
                        self.assertFalse(world.is_blocked(position, 0.02, 1.8),
                                         f"{door.name}: blocked door swing at frame {frame}, sample {sample}")

    def test_ceiling_skins_follow_slabs_and_leave_both_stair_openings_clear(self):
        for name in ("peaceful", "start"):
            level = create_level(name)
            ceilings = [b for b in level.decorations
                        if b.material in ("ceiling_clean", "ceiling_stained", "ceiling_acoustic_panels")]
            self.assertTrue(ceilings)
            for panel in ceilings:
                with self.subTest(world=name, panel=panel.position):
                    floor = min((4.8, 9.6, 14.4), key=lambda y: abs(y - panel.position[1]))
                    self.assertAlmostEqual(panel.collider.top, floor - 0.24, places=5)
                    if floor < 14.4:
                        for angle in range(0, 360, 10):
                            rad = math.radians(angle)
                            x, z = -13 + 2.875 * math.cos(rad), 4 + 2.875 * math.sin(rad)
                            self.assertFalse(panel.footprint.intersects_circle(x, z, 0.3))

    def test_patient_beds_have_small_wall_gaps_and_grounded_legs(self):
        beds = [b for b in self.level.boxes
                if b.size == (1.18, 0.2, 2.15) and b.position[1] > 9.6 and b.position[2] < -10]
        self.assertEqual(len(beds), 8)
        for bed in beds:
            self.assertAlmostEqual(bed.footprint.min_z - (-23.86), 0.08, places=5)
            left_wall = min((-29.86, -20.88, -13.88, -6.88, 0.12, 7.12, 14.12, 21.12),
                            key=lambda x: abs(x - bed.footprint.min_x))
            # The headboard extends 2 cm farther than the mattress frame.
            self.assertAlmostEqual(bed.footprint.min_x - left_wall, 0.12, places=5)
            legs = [b for b in self.level.boxes if b.size == (0.08, 0.32, 0.08)
                    and abs(b.position[0] - bed.position[0]) < 0.5
                    and abs(b.position[2] - bed.position[2]) < 0.9
                    and abs(b.collider.bottom - 9.6) < 1e-5]
            self.assertEqual(len(legs), 4)

    def test_patient_rooms_share_partitions_and_building_envelope(self):
        for x, z in ((-21, -23), (21, -23), (2, 23), (16, 23),
                     (3, 14), (17, 14), (-29, 14), (29, -4), (29, 8), (-10, -6)):
            with self.subTest(partition=(x, z)):
                self.assertTrue(self.world.is_blocked(glm.vec3(x, 9.6, z), 0.25, 1.8))

    def test_nurse_office_does_not_overlap_neighboring_ward_doorways(self):
        doors = {obj.name: obj for obj in self.doors}
        self.assertNotIn("f3_patient_nurse_inner", doors)
        entrance = doors["f3_patient_nurse_room"].states["default"].boxes[0]
        self.assertEqual((entrance.position[0], entrance.position[2]), (-7, -4))
        # Walk into each ward from the hall and back, without entering the office.
        # This covers the full approach, not just a short crossing of the door panel.
        for x in (-12, -2):
            with self.subTest(ward_door=x):
                body = make_body(self.world, (x, 9.6, -6))
                walk(self, body, ((x, 9.6, -12), (x, 9.6, -6)), fps=30)
        body = make_body(self.world, (-7, 9.6, -2))
        walk(self, body, ((-7, 9.6, -6), (-7, 9.6, -2)), fps=30)

    def test_rearranged_upper_rooms_remain_reachable_from_the_landings(self):
        scene = Campaign().load_level("start")
        ally = scene.session.companions[0]
        for obj in scene.level.objects:
            if "open" in obj.states:
                obj.set_state("open")
                obj.update(1)
        goals = [(x, 4.8, -18) for x in (-24, -16, -8, 0, 8, 16, 24)]
        goals += [(x - 1.6, 9.6, -19) for x in (-24.5, -17.5, -10.5, -3.5, 3.5, 10.5, 17.5, 24.5)]
        goals += [(22, 9.6, 1), (-5.5, 9.6, 18), (10, 9.6, 18), (23, 9.6, 18)]
        for goal in goals:
            with self.subTest(goal=goal):
                self.assertFalse(ally.body.world.is_blocked(glm.vec3(goal), 0.25, 1.8))
                route = scene.level.navigation.find_path((-7, goal[1], 6.9), goal, ally._navigation)
                self.assertTrue(route.complete, f"No route to {goal}: {route.points}")
