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
                point = glm.vec3(stair.point(angle, 4.34, height + 0.35))
                self.assertTrue(world.is_blocked(point, 0.02, 0.1), (angle, height))

    def test_plan_has_six_offices_and_correct_scale(self):
        level = create_level("start")
        self.assertEqual(level.floor_size, (43, 29))
        self.assertEqual(level.floor_heights, (0, 4.8, 9.6))
        names = {obj.name for obj in level.objects}
        self.assertTrue({f"office_{i}" for i in range(6)} <= names)
        self.assertTrue({"main_entrance_0", "side_entrance_0", "registration_0"} <= names)
        self.assertTrue({f"f{floor}_office_{i}" for floor in (2, 3) for i in range(6)} <= names)
        self.assertFalse({f"f{floor}_main_entrance_0" for floor in (2, 3)} & names)

    def test_hospital_doors_open_without_keys(self):
        scene = Campaign().load_level("start")
        door = next(obj for obj in scene.level.objects if obj.name == "office_0")
        self.assertEqual(door.interaction.command, "open_door")
        scene.player._interactions._activate(door)
        door.update(1)
        self.assertEqual(door.current_state, door.states["open"])

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
                         (-19, 0, -0.9), (-13, 0, -0.9), (-13, 0, -4.5)))
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
            walk(self, body, ((-12.2, height, 6.9), (-8, height, 6.9), (-8, height, 10.5),
                             (-3, height, 10.5), (3.5, height, 10.5), (3.5, height, -4.5),
                             (4, height, -4.5), (4, height, -8), (4, height, -4.5)))
            self.assertAlmostEqual(body.position.y, height, places=4)
            self.assertTrue(body.grounded)
            if flight + 1 < stair.flights:
                walk(self, body, ((3.5, height, -4.5), (3.5, height, 10.5), (-3, height, 10.5),
                                 (-8, height, 10.5), (-8, height, 6.9), (-12.2, height, 6.9)))

    def test_invalid_stair_dimensions_are_rejected(self):
        for values in ({"steps": 0}, {"inner_radius": -1}, {"height": float("nan")},
                       {"inner_radius": 5, "outer_radius": 4}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                SpiralStair(**values)


if __name__ == "__main__":
    unittest.main()
