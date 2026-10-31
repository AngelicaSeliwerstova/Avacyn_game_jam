import unittest
from dataclasses import replace
import math
from pathlib import Path
import tempfile

import glm

from engine.collision.world3d import CollisionWorld3D
from engine.physics.character import CharacterBody
from engine.input.state import InputState
from game.campaign import Campaign
from game.entities.player import create_player
from game.interactions import InteractionController
from game.levels import create_level
from game.levels.hospital import OFFICE_DOORS
from game.levels.spiral import SpiralStair


def make_body(world, position):
    return CharacterBody(position, world, radius=0.25, height=1.8, step_height=0.3,
                         gravity=18, collision_max_step=0.1, physics_step=1 / 120,
                         camera_smoothing=12, jump_height=0.9)


def walk(test, body, points, fps=60):
    for point in points:
        for _ in range(fps * 20):
            delta = glm.vec3(point[0] - body.position.x, 0, point[2] - body.position.z)
            distance = glm.length(delta)
            if distance < 0.045:
                break
            body.update(1 / fps, glm.normalize(delta) * min(2.3, distance * 25))
        else:
            test.fail(f"Player stuck at {tuple(body.position)} while walking to {point}")
        test.assertFalse(body.world.is_blocked(body.position, body.radius - 1e-4, body.height - 1e-4))


class HospitalTests(unittest.TestCase):
    def test_stair_handrails_do_not_intersect_gallery_handrails(self):
        stair = SpiralStair()
        caps = [b for b in stair.build() if b.size[1] < 0.2
                and math.hypot(b.position[0] + 13, b.position[2] - 4) > 4]
        for angle in range(360):
            x, _, z = stair.point(angle, stair.gallery_radius - 0.13)
            self.assertFalse(any(b.footprint.intersects_circle(x, z, 0.005) for b in caps), angle)

    def test_gallery_guards_last_steps_and_top_bridge_inner_edge(self):
        level = create_level("start")
        world = CollisionWorld3D((b.collider for b in level.boxes), level.floor_bounds)
        stair = SpiralStair()
        for flight in range(stair.flights):
            for step in range(stair.steps - 7, stair.steps):
                top = stair.step_height(flight * stair.steps + step)
                point = stair.point(90 - (step + 0.5) * 360 / stair.steps, stair.gallery_radius, top)
                self.assertTrue(world.is_blocked(glm.vec3(point), 0.1, 1.8))
        for x in (-12.8, -12, -11, -10, -9):
            self.assertTrue(world.is_blocked(glm.vec3(x, 9.6, 5.46), 0.1, 1.8))

    def test_overlapping_gallery_floor_uses_one_material(self):
        level = create_level("start")
        for height in (4.8, 9.6):
            for x, z in ((-9, 8.06), (-9.43, 7.91), (-17.5, 8.4), (-7.5, 6.9)):
                materials = {b.material for b in level.boxes if abs(b.collider.top - height) < 1e-5
                             and b.footprint.intersects_circle(x, z, 0.00001)}
                self.assertEqual(materials, {"concrete_cracked"}, (x, z, height))
    def test_gallery_floor_covers_radial_slab_seams(self):
        level = create_level("start")
        for height in (4.8, 9.6):
            footprints = [box.footprint for box in level.boxes if abs(box.collider.top - height) < 1e-5]
            for i in range(93):
                for j in range(93):
                    x, z = -17.6 + i * 0.1, -0.6 + j * 0.1
                    if math.hypot(x + 13, z - 4) < 4.45:
                        continue
                    self.assertTrue(any(f.intersects_circle(x, z, 0.00001) for f in footprints), (x, z, height))
            self.assertTrue(any(f.intersects_circle(-9.43, 7.91, 0.00001) for f in footprints))
        world = CollisionWorld3D((b.collider for b in level.boxes), level.floor_bounds)
        self.assertEqual(world.support_height(glm.vec3(-13, 9.6, 4), 0.01, 9.6), 0)

    def test_gallery_parapet_is_solid_below_the_handrail(self):
        level = create_level("start")
        world = CollisionWorld3D((b.collider for b in level.boxes), level.floor_bounds)
        stair = SpiralStair()
        for height in (4.8, 9.6):
            for angle in range(0, 360, 3):
                if 17 < angle < 78:
                    continue
                point = glm.vec3(stair.point(angle, stair.gallery_radius, height + 0.35))
                self.assertTrue(world.is_blocked(point, 0.02, 0.1), (angle, height))

    def test_plan_has_six_offices_and_correct_scale(self):
        level = create_level("start")
        self.assertEqual(level.floor_size, (60, 48))
        self.assertEqual(level.floor_heights, (0, 4.8, 9.6))
        self.assertEqual(level.floor_labels, ("1", "2 — хирургия", "3 — пациентское отделение"))
        self.assertEqual(level.floor_hints[1], "Хирургическое отделение")
        self.assertEqual(level.floor_hints[2], "Пациентское отделение")
        names = {obj.name for obj in level.objects}
        self.assertTrue({f"office_{i}" for i in range(6)} <= names)
        self.assertTrue({"main_entrance_0", "side_entrance_0", "registration_0"} <= names)
        self.assertTrue({"f2_surgery_or_1", "f2_surgery_or_2", "f2_surgery_electrical"} <= names)
        self.assertTrue({f"f3_patient_room_{i}" for i in range(8)} <= names)
        self.assertFalse({f"f{floor}_main_entrance_0" for floor in (2, 3)} & names)

    def test_surgical_wing_fills_expanded_floor_and_has_no_puzzle_locks(self):
        level = create_level("start")
        names = {obj.name for obj in level.objects}
        expected_rooms = {
            "f2_surgery_xray", "f2_surgery_preop", "f2_surgery_or_1",
            "f2_surgery_surgeon", "f2_surgery_sterilization", "f2_surgery_or_2",
            "f2_surgery_pharmacy", "f2_surgery_nurses", "f2_surgery_recovery",
            "f2_surgery_staff", "f2_surgery_electrical",
        }
        self.assertTrue(expected_rooms <= names)
        operating_rooms = {obj.name: obj for obj in level.objects if obj.name in (
            "f2_surgery_or_1", "f2_surgery_or_2",
        )}
        self.assertEqual(set(operating_rooms), {"f2_surgery_or_1", "f2_surgery_or_2"})
        surgery_doors = [obj.name for obj in level.objects if obj.name.startswith("f2_surgery_")]
        self.assertEqual(len(surgery_doors), len(set(surgery_doors)))
        self.assertEqual(sum(box.size == (1.18, 0.2, 2.15) and 4.8 < box.position[1] < 9.6
                             for box in level.boxes), 6)
        self.assertEqual(sum(box.size == (1.18, 0.2, 2.15) and box.position[1] > 9.6
                             for box in level.boxes), 18)
        self.assertTrue(all(obj.interaction.command == "open_door" for obj in operating_rooms.values()))
        world = CollisionWorld3D((box.collider for box in level.boxes), level.floor_bounds)
        self.assertAlmostEqual(world.support_height(glm.vec3(27, 4.8, 20), 0.1, 4.8), 4.8)
        self.assertTrue(any(abs(point[1] - 4.8) < 0.01 and math.dist(point, (24, 4.8, 18)) < 1.6
                            for point in level.navigation.points))
        for angle in range(0, 360, 15):
            point = glm.vec3(SpiralStair().point(angle, 4.5, 4.8))
            self.assertAlmostEqual(world.support_height(point, 0.01, 4.8), 4.8, places=4)
        roof = [box for box in level.boxes if abs(box.collider.top - 14.4) < 1e-5
                and box.footprint.intersects_circle(27, 21, 0.01)]
        self.assertTrue(roof)
        upper_floor = [box for box in level.boxes if abs(box.collider.top - 9.6) < 1e-5
                       and box.footprint.intersects_circle(27, 21, 0.01)]
        self.assertTrue(upper_floor)

    def test_surgical_floor_is_enclosed_by_walls_on_all_sides(self):
        level = create_level("start")
        world = CollisionWorld3D((box.collider for box in level.boxes), level.floor_bounds)
        for point in ((0, 4.8, -24), (0, 4.8, 24), (-30, 4.8, 0), (30, 4.8, 0)):
            with self.subTest(point=point):
                self.assertTrue(world.is_blocked(glm.vec3(point), 0.25, 1.8))

    def test_patient_floor_has_eight_open_rooms_and_supported_wings(self):
        level = create_level("start")
        patient_rooms = [obj for obj in level.objects
                         if obj.name.startswith("f3_patient_room_") and not obj.name.endswith("_frame")]
        self.assertEqual(len(patient_rooms), 8)
        self.assertTrue(all(obj.interaction.command == "open_door" for obj in patient_rooms))
        names = {obj.name for obj in level.objects}
        self.assertTrue({
            "f3_patient_nurse_room", "f3_patient_nurse_inner",
            "f3_patient_east_entry", "f3_patient_south_west",
            "f3_patient_south_center", "f3_patient_south_east",
        } <= names)
        world = CollisionWorld3D((box.collider for box in level.boxes), level.floor_bounds)
        for point in ((-25, 9.6, -17), (24, 9.6, -17), (24, 9.6, 18)):
            self.assertAlmostEqual(world.support_height(glm.vec3(point), 0.1, 9.6), 9.6)
        roof = [box for box in level.boxes if abs(box.collider.top - 14.4) < 1e-5
                and box.footprint.intersects_circle(27, 21, 0.01)]
        self.assertTrue(roof)

    def test_patient_floor_is_enclosed_by_walls_on_all_sides(self):
        level = create_level("start")
        world = CollisionWorld3D((box.collider for box in level.boxes), level.floor_bounds)
        for point in ((0, 9.6, -24), (0, 9.6, 24), (-30, 9.6, 0), (30, 9.6, 0)):
            with self.subTest(point=point):
                self.assertTrue(world.is_blocked(glm.vec3(point), 0.25, 1.8))

    def test_hospital_doors_open_without_keys(self):
        scene = Campaign().load_level("start")
        door = next(obj for obj in scene.level.objects if obj.name == "office_0")
        self.assertEqual(door.interaction.command, "open_door")
        scene.player._interactions._activate(door)
        door.update(1)
        self.assertEqual(door.current_state, door.states["open"])

    def test_exterior_doors_are_closed_elevators_with_a_warning(self):
        for level_name in ("start", "peaceful"):
            with self.subTest(level=level_name):
                level = create_level(level_name)
                doors = {obj.name: obj for obj in level.objects
                         if obj.name in ("main_entrance_0", "side_entrance_0")}
                self.assertEqual(set(doors), {"main_entrance_0", "side_entrance_0"})
                for door in doors.values():
                    self.assertEqual(tuple(door.states), ("default",))
                    self.assertEqual(door.interaction.action, "Не пользоваться")
                    self.assertEqual(door.interaction.message, "Лифтом лучше не пользоваться.")
                    self.assertEqual({box.material for box in door.boxes}, {"metal_scratched_dark"})
                    interactions = InteractionController((), 3, 2, "E", objects=(door,))
                    self.assertEqual(interactions._activate(door), "Лифтом лучше не пользоваться.")
                    self.assertEqual(door.state_name, "default")
                frames = {obj.name: obj for obj in level.objects
                          if obj.name in ("main_entrance_0_frame", "side_entrance_0_frame")}
                self.assertEqual(len(frames), 2)
                self.assertTrue(all(any(box.emission == (0.8, 0.04, 0.02) for box in frame.boxes)
                                    for frame in frames.values()))

    def test_creator_can_place_lamp_on_upper_gallery_ceiling(self):
        level = create_level("start")
        with tempfile.TemporaryDirectory() as directory:
            level = replace(level, spawn_position=(-7, 6.4, 7), spawn_target=(-7, 6.4, 6),
                            creator_lights_path=Path(directory) / "lights.json")
            world = CollisionWorld3D((box.collider for box in level.boxes), level.floor_bounds,
                                     objects=level.objects)
            player = create_player(level, world, creator_mode=True)
            player._creator_yaw = 0
            player._creator_pitch = math.radians(80)
            player.update(0, InputState(add_creator_light=True))
            self.assertEqual(len(player.creator_lights), 1)
            self.assertAlmostEqual(player.creator_lights[0].position[1], 9.12, places=4)

    def test_spiral_ascends_and_descends_in_complete_hospital(self):
        level = create_level("start")
        world = CollisionWorld3D((b.collider for b in level.boxes), level.floor_bounds,
                                 objects=level.objects)
        stair = SpiralStair()
        for fps in (30, 60, 120):
            with self.subTest(fps=fps):
                body = make_body(world, (-12.95, 0, 8.6))
                radius = (stair.inner_radius + stair.outer_radius) / 2
                points = (stair.point(89, radius), *stair.walking_path(),
                          (-12.2, 9.6, 6.9), (-7.0, 9.6, 6.9))
                walk(self, body, points, fps)
                self.assertAlmostEqual(body.position.y, stair.total_height, places=4)
                self.assertTrue(body.grounded)
                walk(self, body, (*reversed(points[:-1]), (-12.95, 0, 8.6)), fps)
                self.assertAlmostEqual(body.position.y, 0.0, places=4)
                self.assertTrue(body.grounded)

    def test_ground_floor_rooms_connect_through_doorways(self):
        level = create_level("start")
        for obj in level.objects:
            if "open" in obj.states:
                obj.set_state("open")
                obj.update(1)
        world = CollisionWorld3D((b.collider for b in level.boxes), level.floor_bounds,
                                 objects=level.objects)
        body = make_body(world, (-0.5, 0, 12.2))
        walk(self, body, ((-5, 0, 10.5), (-9, 0, 10.5), (-12.95, 0, 8.6),
                         (-12, 0, 8.5), (-12, 0, 6.5), (-19, 0, 6.5),
                         (-19, 0, -0.9), (-18.5, 0, -0.9), (-18.5, 0, -4.5)))
        for x in OFFICE_DOORS:
            walk(self, body, ((x, 0, -4.5), (x, 0, -8), (x, 0, -4.5)))
        # Регистрация, проход в охрану и возвращение в главный холл.
        walk(self, body, ((11, 0, -4.5), (11, 0, 0), (12, 0, 0), (12, 0, 4.3),
                         (14.3, 0, 4.3), (14.3, 0, 5.3), (12, 0, 4.3), (12, 0, 0),
                         (3.5, 0, 0), (3.5, 0, 10.5), (-0.5, 0, 10.5), (3.5, 0, 10.5),
                         (3.5, 0, 2.2), (-1, 0, 2.2), (-1, 0, 4.5), (-1, 0, 2.2),
                         (-1, 0, -4.5)))
        self.assertAlmostEqual(body.position.y, 0, places=4)

    def test_reported_corridor_partition_is_clear_on_every_floor(self):
        level = create_level("start")
        world = CollisionWorld3D((b.collider for b in level.boxes), level.floor_bounds,
                                 objects=level.objects)
        for height in level.floor_heights:
            body = make_body(world, (12, height, -3.5))
            walk(self, body, ((12, height, 0),))
            self.assertAlmostEqual(body.position.y, height, places=4)

    def test_stair_landings_connect_to_second_and_third_floor_rooms(self):
        level = create_level("start")
        for obj in level.objects:
            if "open" in obj.states:
                obj.set_state("open")
                obj.update(1)
        world = CollisionWorld3D((b.collider for b in level.boxes), level.floor_bounds,
                                 objects=level.objects)
        stair = SpiralStair()
        body = make_body(world, (-12.95, 0, 8.6))
        path = stair.walking_path()
        radius = (stair.inner_radius + stair.outer_radius) / 2
        walk(self, body, (stair.point(89, radius),))
        for flight in range(stair.flights):
            walk(self, body, path[flight * stair.steps:(flight + 1) * stair.steps])
            height = (flight + 1) * stair.height
            if flight == 0:
                walk(self, body, ((-12.2, height, 6.9), (-8, height, 6.9), (-8, height, 10.5),
                                 (-3, height, 10.5), (3.5, height, 10.5), (10, height, 10.5),
                                 (10, height, 1), (20, height, 1)))
            else:
                walk(self, body, ((-12.2, height, 6.9), (-8, height, 6.9), (-8, height, 10.5),
                                 (-3, height, 10.5), (3.5, height, 10.5), (3.5, height, -4.5),
                                 (4, height, -4.5), (4, height, -8), (4, height, -4.5)))
            self.assertAlmostEqual(body.position.y, height, places=4)
            self.assertTrue(body.grounded)
            if flight + 1 < stair.flights:
                if flight == 0:
                    walk(self, body, ((20, height, 1), (10, height, 1), (10, height, 10.5),
                                     (3.5, height, 10.5), (-3, height, 10.5),
                                     (-8, height, 10.5), (-8, height, 6.9), (-12.2, height, 6.9)))
                else:
                    walk(self, body, ((3.5, height, -4.5), (3.5, height, 10.5), (-3, height, 10.5),
                                     (-8, height, 10.5), (-8, height, 6.9), (-12.2, height, 6.9)))

    def test_invalid_stair_dimensions_are_rejected(self):
        for values in ({"steps": 0}, {"inner_radius": -1}, {"height": float("nan")},
                       {"inner_radius": 5, "outer_radius": 4}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                SpiralStair(**values)


if __name__ == "__main__":
    unittest.main()
