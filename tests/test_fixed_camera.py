from dataclasses import replace
from pathlib import Path
import math
import tempfile
import unittest
from unittest.mock import patch

import glm

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.input.state import InputState
from engine.scene.box import Box
from engine.scene.camera import FixedCameraZone
from engine.scene.level import Level
from game.levels.cameras import camera_model_boxes, load_fixed_cameras, save_fixed_cameras
from game.levels.creator import load_creator_objects
from game.levels.creator_lights import load_creator_lights
from game.entities.player import create_player
from game.levels import create_level


class FixedCameraTests(unittest.TestCase):
    def test_camera_zone_checks_its_bounds_and_rejects_invalid_dimensions(self):
        zone = FixedCameraZone(
            minimum=(0, 0, 0), maximum=(2, 2, 2),
            position=(0, 1, 1), target=(1, 1, 1),
        )
        self.assertTrue(zone.contains((1, 1, 1)))
        self.assertFalse(zone.contains((2.1, 1, 1)))
        with self.assertRaises(ValueError):
            FixedCameraZone(
                minimum=(0, 0, 0), maximum=(0, 2, 2),
                position=(0, 1, 1), target=(1, 1, 1),
            )

    def test_player_keeps_a_fixed_view_outside_camera_zones(self):
        zone = FixedCameraZone(
            minimum=(5, 0, 5), maximum=(7, 3, 7),
            position=(6, 2, 6), target=(6, 2, 5),
        )
        level = Level(
            (20, 20), 1, (), (0, settings.PLAYER_EYE_HEIGHT, 0),
            (0, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
            fixed_cameras=(zone,),
        )
        world = CollisionWorld3D((), level.floor_bounds)
        player = create_player(level, world)

        player.update(0, InputState())

        self.assertEqual(tuple(player.camera.position), zone.position)
        self.assertEqual(tuple(player.camera.target), zone.target)

    def test_authored_camera_replaces_automatic_view_when_both_zones_match(self):
        authored = FixedCameraZone(
            minimum=(-1, -1, -1), maximum=(1, 3, 1),
            position=(0, 2, 0), target=(0, 2, -4),
        )
        automatic = FixedCameraZone(
            minimum=(-1, -1, -1), maximum=(1, 3, 1),
            position=(10, 2, 10), target=(10, 2, 8),
        )
        level = Level(
            (20, 20), 1, (), (0, settings.PLAYER_EYE_HEIGHT, 0),
            (0, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
            fixed_cameras=(authored, automatic), fixed_cameras_authored=True,
            authored_fixed_cameras=(authored,),
        )
        player = create_player(level, CollisionWorld3D((), level.floor_bounds))

        player.update(0, InputState())

        self.assertEqual(player._camera_zones, (authored,))
        self.assertLess(glm.length(player.camera.position - player._camera_view_position(authored)), 1e-5)
        self.assertEqual(tuple(player.camera.target), authored.target)

    def test_walking_forward_follows_fixed_camera_view(self):
        zone = FixedCameraZone(
            minimum=(-2, -1, -2), maximum=(2, 3, 2),
            position=(-3, 2, 0), target=(1, 2, 0),
        )
        level = Level(
            (20, 20), 1, (), (0, settings.PLAYER_EYE_HEIGHT, 0),
            (0, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
            fixed_cameras=(zone,),
        )
        player = create_player(level, CollisionWorld3D((), level.floor_bounds))

        player.update(0.1, InputState(forward=1))

        self.assertGreater(player.body.position.x, 0)
        self.assertAlmostEqual(player.body.position.z, 0, places=5)

    def test_held_movement_does_not_reverse_when_crossing_camera_boundary(self):
        first = FixedCameraZone(
            minimum=(-2, -1, -2), maximum=(0, 3, 2),
            position=(-1, 2, -3), target=(1, 2, 0),
        )
        second = FixedCameraZone(
            minimum=(0, -1, -2), maximum=(2, 3, 2),
            position=(1, 2, 3), target=(-1, 2, 0),
        )
        level = Level(
            (20, 20), 1, (), (-0.1, settings.PLAYER_EYE_HEIGHT, 0),
            (-0.1, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
            fixed_cameras=(first, second),
        )
        player = create_player(level, CollisionWorld3D((), level.floor_bounds))

        player.update(0.1, InputState(forward=1))
        crossed_boundary_x = player.body.position.x
        self.assertGreater(crossed_boundary_x, 0)
        self.assertIs(player._active_fixed_camera(), first)

        player.update(0.1, InputState(forward=1))

        self.assertGreater(player.body.position.x, crossed_boundary_x)

    def test_held_movement_keeps_world_direction_if_camera_must_switch(self):
        first = FixedCameraZone(
            minimum=(-2, -1, -2), maximum=(0, 3, 2),
            position=(-1, 2, -3), target=(1, 2, 0),
        )
        second = FixedCameraZone(
            minimum=(0, -1, -2), maximum=(2, 3, 2),
            position=(1, 2, 3), target=(-1, 2, 3),
        )
        level = Level(
            (20, 20), 1, (), (-0.1, settings.PLAYER_EYE_HEIGHT, 0),
            (-0.1, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
            fixed_cameras=(first, second),
        )
        player = create_player(level, CollisionWorld3D((), level.floor_bounds))

        def framing_score(zone, point):
            if zone is first:
                return 0.0 if point[0] <= 0 else None
            return 0.0 if point[0] > 0 else None

        with patch.object(player, "_fixed_camera_framing_score", side_effect=framing_score):
            self.assertIs(player._active_fixed_camera(), first)
            player.update(0.1, InputState(forward=1))
            self.assertIs(player._active_fixed_camera(), second)
            crossed_boundary_x = player.body.position.x
            player.update(0.1, InputState(forward=1))

        self.assertGreater(player.body.position.x, crossed_boundary_x)

    def test_overlapping_camera_zones_keep_current_camera_until_player_leaves_its_zone(self):
        first = FixedCameraZone(
            minimum=(-2, -1, -2), maximum=(0.5, 3, 2),
            position=(0, 2, -3), target=(0, 2, 0),
        )
        second = FixedCameraZone(
            minimum=(-0.5, -1, -2), maximum=(2, 3, 2),
            position=(0, 2, 3), target=(0, 2, 0),
        )
        level = Level(
            (20, 20), 1, (), (0, settings.PLAYER_EYE_HEIGHT, 0),
            (0, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
            fixed_cameras=(first, second),
        )
        player = create_player(level, CollisionWorld3D((), level.floor_bounds))

        self.assertIs(player._active_fixed_camera(), first)
        player.body._position.x = 0.25
        self.assertIs(player._active_fixed_camera(), first)
        player.body._position.x = 0.95
        self.assertIs(player._active_fixed_camera(), second)
        self.assertTrue(player.fixed_camera_effect_active)
        self.assertEqual(player.camera_transition_strength, 1.0)
        player.update(0.1, InputState())
        self.assertGreater(player.camera_transition_strength, 0.0)
        self.assertLess(player.camera_transition_strength, 1.0)
        player.update(0.2, InputState())
        self.assertEqual(player.camera_transition_strength, 0.0)

    def test_camera_selection_uses_player_eye_height_for_zone_membership(self):
        first = FixedCameraZone(
            minimum=(-2, 1, -2), maximum=(0, 3, 2),
            position=(-1, 2, -3), target=(-1, 2, 0),
        )
        second = FixedCameraZone(
            minimum=(0, 1, -2), maximum=(2, 3, 2),
            position=(1, 2, 3), target=(1, 2, 0),
        )
        level = Level(
            (20, 20), 1, (), (0, settings.PLAYER_EYE_HEIGHT, 0),
            (0, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
            fixed_cameras=(first, second),
        )
        player = create_player(level, CollisionWorld3D((), level.floor_bounds))

        self.assertIs(player._active_fixed_camera(), first)
        player.body._position.x = 0.12
        self.assertIs(player._active_fixed_camera(), first)
        player.body._position.x = 0.8
        self.assertIs(player._active_fixed_camera(), second)

    def test_player_uses_nearest_authored_camera_outside_its_zone(self):
        authored = FixedCameraZone(
            minimum=(8, 1, 8), maximum=(12, 3, 12),
            position=(10, 2, 8), target=(10, 2, 12),
        )
        level = Level(
            (30, 30), 1, (), (0, settings.PLAYER_EYE_HEIGHT, 0),
            (0, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
            fixed_cameras=(authored,), fixed_cameras_authored=True,
            authored_fixed_cameras=(authored,),
        )
        player = create_player(level, CollisionWorld3D((), level.floor_bounds))

        self.assertEqual(player._automatic_camera_zones, ())
        self.assertIs(player._active_fixed_camera(), authored)

    def test_switches_to_camera_framing_player_when_current_camera_loses_them(self):
        first = FixedCameraZone(
            minimum=(-1, 1, -1), maximum=(1, 3, 1),
            position=(0, 2, 0), target=(0, 2, 1),
        )
        second = FixedCameraZone(
            minimum=(8, 1, 8), maximum=(12, 3, 12),
            position=(10, 2, 8), target=(10, 2, 12),
        )
        level = Level(
            (30, 30), 1, (), (0, settings.PLAYER_EYE_HEIGHT, 0),
            (0, settings.PLAYER_EYE_HEIGHT, 1), ((80, 80, 80),) * 2,
            fixed_cameras=(first, second),
        )
        player = create_player(level, CollisionWorld3D((), level.floor_bounds))

        self.assertIs(player._active_fixed_camera(), first)
        player.body._position.x = 10
        player.body._position.z = 10
        self.assertIs(player._active_fixed_camera(), second)

    def test_keeps_camera_that_frames_player_instead_of_switching_to_nearest_blind_camera(self):
        first = FixedCameraZone(
            minimum=(-28, 1, 18), maximum=(-22, 3.6, 23.5),
            position=(-25.29697, 2.84995, 19.66),
            target=(-26.37458, 0.93355, 27.35194),
        )
        second = FixedCameraZone(
            minimum=(-23.5, 1, 22), maximum=(-18.5, 3.7, 27.1),
            position=(-19.66, 2.98645, 24.57948),
            target=(-23.03843, -0.69390, 18.33120),
        )
        level = Level(
            (60, 60), 1, (), (-25.75, settings.PLAYER_EYE_HEIGHT, 25.49),
            (-25.75, settings.PLAYER_EYE_HEIGHT, 24.49), ((80, 80, 80),) * 2,
            fixed_cameras=(first, second),
        )
        player = create_player(level, CollisionWorld3D((), level.floor_bounds))

        self.assertIs(player._active_fixed_camera(), first)
        player.body._position.x -= 0.2
        self.assertIsNotNone(player._fixed_camera_framing_score(first, player._player_eye_position()))
        self.assertIsNone(player._fixed_camera_framing_score(second, player._player_eye_position()))
        self.assertIs(player._active_fixed_camera(), first)

    def test_outside_camera_zones_prefers_nearest_visible_camera_over_best_framing(self):
        nearest = FixedCameraZone(
            minimum=(-27.8, 1.0, 18.5), maximum=(-22.8, 3.55, 23.5),
            position=(-25.3, 2.85, 19.66), target=(-26.37, 0.93, 27.35),
        )
        better_framing = FixedCameraZone(
            minimum=(-18.54, 0.63, 18.5), maximum=(-13.54, 3.18, 23.5),
            position=(-16.04, 2.48, 19.66), target=(-22.6, 0.1, 23.57),
        )
        level = Level(
            (60, 60), 1, (), (-28.25, settings.PLAYER_EYE_HEIGHT, 24.09),
            (-28.25, settings.PLAYER_EYE_HEIGHT, 23.09), ((80, 80, 80),) * 2,
            fixed_cameras=(nearest, better_framing),
        )
        player = create_player(level, CollisionWorld3D((), level.floor_bounds))

        self.assertLess(
            player._fixed_camera_framing_score(better_framing, player._player_eye_position()),
            player._fixed_camera_framing_score(nearest, player._player_eye_position()),
        )
        self.assertIs(player._active_fixed_camera(), nearest)

    def test_camera_selection_rejects_view_blocked_by_wall(self):
        blocked_camera = FixedCameraZone(
            minimum=(-2, -1, -2), maximum=(2, 3, 2),
            position=(0, 1.6, -4), target=(0, 1.6, 4),
        )
        clear_camera = FixedCameraZone(
            minimum=(-2, -1, -2), maximum=(2, 3, 2),
            position=(3, 1.6, 0), target=(0, 1.6, 0),
        )
        wall = Box((0, 1.5, -1), (2, 3, 0.2))
        level = Level(
            (20, 20), 1, (wall,), (0, settings.PLAYER_EYE_HEIGHT, 0),
            (0, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
            fixed_cameras=(blocked_camera, clear_camera),
        )
        player = create_player(level, CollisionWorld3D((wall.collider,), level.floor_bounds))

        self.assertIsNone(player._fixed_camera_framing_score(
            blocked_camera, player._player_eye_position(),
        ))
        self.assertIsNotNone(player._fixed_camera_framing_score(
            clear_camera, player._player_eye_position(),
        ))
        player._active_camera_zone = blocked_camera
        self.assertIs(player._active_fixed_camera(), clear_camera)

    def test_camera_layout_round_trips_and_model_led_flashes(self):
        zone = FixedCameraZone(
            minimum=(-1, 0, -1), maximum=(1, 3, 1),
            position=(0, 2, 0), target=(0, 1, -2),
        )
        on = camera_model_boxes(zone, True)
        off = camera_model_boxes(zone, False)
        self.assertEqual(len(on), 10)
        self.assertNotEqual(on[-1].emission, off[-1].emission)
        self.assertEqual(on[3].size, (0.34, 0.24, 0.36))
        self.assertEqual(on[7].color, (0.012, 0.035, 0.045))
        self.assertGreater(on[0].position[2], on[5].position[2])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "maze_cameras.json"
            self.assertIsNone(load_fixed_cameras(path))
            save_fixed_cameras(path, (zone,))
            self.assertEqual(load_fixed_cameras(path), (zone,))
            save_fixed_cameras(path, ())
            self.assertEqual(load_fixed_cameras(path), ())

    def test_in_game_editor_places_saves_and_deletes_camera(self):
        wall = Box((0, 1.6, -4), (6, 3, 0.2), material="concrete")
        level = Level((10, 10), 1, (wall,), (0, 1.6, 0), (0, 1.6, -1), ((80, 80, 80),) * 2)
        world = CollisionWorld3D((wall.collider,), level.floor_bounds)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "maze_cameras.json"
            editable_level = replace(level, camera_save_path=path)
            player = create_player(editable_level, world)

            player.update(0, InputState(toggle_camera_editor=True))
            self.assertIsNotNone(player.creator_help_text)
            player.update(0, InputState(add_camera=True))
            cameras = load_fixed_cameras(path)
            self.assertEqual(len(cameras), 1)
            camera = cameras[0]
            self.assertAlmostEqual(camera.position[2], wall.collider.footprint.max_z + 0.16, places=5)
            self.assertGreater(camera.target[2], camera.position[2])
            self.assertEqual(len(player.camera_marker_boxes), len(camera_model_boxes(camera, True)))

            player.update(0, InputState(toggle_camera_editor=True))
            self.assertLess(
                glm.length(player.camera.position - player._camera_view_position(camera)), 1e-5,
            )
            self.assertLess(glm.length(player.camera.target - glm.vec3(camera.target)), 1e-5)
            player.update(0, InputState(toggle_camera_editor=True))
            player.camera.position = glm.vec3(camera.position) + glm.vec3(0, 0, 2)
            player._creator_yaw = -math.pi / 2
            player._creator_pitch = 0
            player._update_creator_view()
            player.update(0, InputState(interact=True))
            self.assertIn("EDITING CAMERA", player.aim_text)
            player.update(0.1, InputState(right=1))
            edited = load_fixed_cameras(path)[0]
            self.assertNotEqual(edited.target, camera.target)
            player.update(0, InputState(interact=True))
            self.assertIn("CAMERA SAVED", player.aim_text)
            player.update(0, InputState(delete_camera=True))
            self.assertEqual(load_fixed_cameras(path), ())
            self.assertEqual(player.camera_marker_boxes, ())

    def test_maze_contains_only_authored_cameras(self):
        authored = FixedCameraZone(
            minimum=(-1, -1, -1), maximum=(1, 3, 1),
            position=(0, 2, 0), target=(0, 2, -4),
        )
        with patch("game.levels.maze.load_fixed_cameras", return_value=(authored,)):
            level = create_level("maze")
        self.assertEqual(level.authored_fixed_cameras, (authored,))
        self.assertEqual(level.fixed_cameras, (authored,))

    def test_creator_mode_free_fly_and_persistent_object_placement(self):
        wall = Box((0, 1.6, -4), (6, 3, 0.2), material="concrete")
        level = Level((10, 10), 1, (wall,), (0, 1.6, 0), (0, 1.6, -1), ((80, 80, 80),) * 2)
        world = CollisionWorld3D((wall.collider,), level.floor_bounds)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "maze_objects.json"
            editable_level = replace(level, creator_objects_path=path)
            player = create_player(editable_level, world, creator_mode=True)
            body_position = glm.vec3(player.body.position)
            initial_camera_position = glm.vec3(player.camera.position)

            player.update(0.1, InputState(forward=1))
            self.assertLess(player.camera.position.z, initial_camera_position.z)
            self.assertEqual(player.body.position, body_position)
            player.update(0.1, InputState(creator_up=True))
            self.assertGreater(player.camera.position.y, initial_camera_position.y)
            self.assertEqual(player.body.position, body_position)

            player.update(0, InputState(add_object=True))
            objects = load_creator_objects(path)
            self.assertEqual(len(objects), 1)
            self.assertEqual(objects[0].material, "rust")
            self.assertAlmostEqual(objects[0].position[2], wall.collider.footprint.max_z + 0.31, places=5)
            self.assertIn(objects[0].collider, world.colliders)
            self.assertTrue(world.is_blocked(
                glm.vec3(objects[0].position), player.body.radius, player.body.height,
            ))

            player.update(0, InputState(delete_camera=True))
            self.assertEqual(load_creator_objects(path), ())

    def test_creator_places_block_on_virtual_basement_floor(self):
        floor_height = -3.6
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "maze_objects.json"
            level = Level(
                (20, 20), 1, (), (0, floor_height + settings.PLAYER_EYE_HEIGHT, 0),
                (0, floor_height + settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
                base_height=floor_height, floor_heights=(floor_height, 0.0, 3.6),
                creator_objects_path=path,
            )
            player = create_player(level, CollisionWorld3D((), level.floor_bounds, floor_height))
            player.update(0, InputState(toggle_camera_editor=True))
            player.camera.position = glm.vec3(0, floor_height + 2.0, 0)
            player._creator_yaw = 0.0
            player._creator_pitch = -math.radians(45)
            player._update_creator_view()

            player.update(0, InputState(add_object=True))

            objects = load_creator_objects(path)
            self.assertEqual(len(objects), 1)
            self.assertAlmostEqual(objects[0].position[1], floor_height + 0.3, places=5)
            self.assertEqual(objects[0].position[2], 0.0)
            self.assertIn("PLACED RUST BLOCK", player.aim_text)

    def test_in_game_editor_places_persists_and_removes_lamps(self):
        wall = Box((0, 1.6, -4), (6, 3, 0.2), material="concrete")
        ceiling = Box((0, 3.15, 0), (6, 0.3, 6), material="concrete")
        level = Level(
            (10, 10), 1, (wall, ceiling), (0, settings.PLAYER_EYE_HEIGHT, 0),
            (0, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
            creator_lights_path=Path("unused_lights.json"),
            creator_room_height=3.0,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "maze_lights.json"
            player = create_player(
                replace(level, creator_lights_path=path),
                CollisionWorld3D((wall.collider, ceiling.collider), level.floor_bounds),
            )
            player.update(0, InputState(toggle_camera_editor=True))
            player.camera.position = glm.vec3(0, 2.0, 0)
            player._creator_yaw = 0.0
            player._creator_pitch = math.radians(80)
            player._update_creator_view()
            player.update(0, InputState(add_creator_light=True))

            lights = load_creator_lights(path)
            self.assertEqual(len(lights), 1)
            self.assertEqual(lights[0].direction, (0.0, -1.0, 0.0))
            self.assertAlmostEqual(lights[0].position[1], 2.76, places=5)
            self.assertEqual(player.creator_lights[-1], lights[0])
            self.assertEqual(len(player.creator_light_boxes), 2)
            self.assertEqual(player.creator_light_boxes[0].size, (1.12, 0.12, 0.52))
            self.assertEqual(player.creator_light_boxes[1].size, (0.92, 0.04, 0.32))
            self.assertIn("PLACED WARM LAMP", player.aim_text)

            player.update(0, InputState(delete_camera=True))
            self.assertEqual(load_creator_lights(path), ())

    def test_creator_lamp_cannot_be_placed_on_wall_or_another_floors_ceiling(self):
        wall = Box((0, 1.6, -4), (6, 3, 0.2), material="concrete")
        upper_ceiling = Box((0, 6.15, 0), (6, 0.3, 6), material="concrete")
        level = Level(
            (10, 10), 1, (wall, upper_ceiling), (0, settings.PLAYER_EYE_HEIGHT, 0),
            (0, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
            creator_lights_path=Path("unused_lights.json"), creator_room_height=3.0,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "maze_lights.json"
            player = create_player(
                replace(level, creator_lights_path=path),
                CollisionWorld3D((wall.collider, upper_ceiling.collider), level.floor_bounds),
            )
            player.update(0, InputState(toggle_camera_editor=True))
            player.camera.position = glm.vec3(0, 2.0, 0)
            player._creator_yaw = 0.0
            player._creator_pitch = math.radians(80)
            player._update_creator_view()
            player.update(0, InputState(add_creator_light=True))

            self.assertEqual(load_creator_lights(path), ())
            self.assertIn("THIS FLOOR'S CEILING", player.aim_text)

            player._creator_pitch = 0.0
            player._creator_yaw = -math.pi / 2
            player._update_creator_view()
            player.update(0, InputState(add_creator_light=True))
            self.assertEqual(load_creator_lights(path), ())

    def test_delete_removes_creator_object_the_camera_is_aimed_at(self):
        near = Box((0, 1.6, -2.0), (0.6, 0.6, 0.6), material="rust")
        far = Box((0, 1.6, -4.0), (0.6, 0.6, 0.6), material="rust")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "maze_objects.json"
            level = Level(
                (10, 10), 1, (), (0, settings.PLAYER_EYE_HEIGHT, 0),
                (0, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
                creator_objects=(near, far), creator_objects_path=path,
            )
            player = create_player(level, CollisionWorld3D((), level.floor_bounds))
            player.update(0, InputState(toggle_camera_editor=True))
            player.camera.position = glm.vec3(0, 1.6, 0)
            player._creator_yaw = -math.pi / 2
            player._creator_pitch = 0.0
            player._update_creator_view()

            player.update(0, InputState(delete_camera=True))

            self.assertEqual(player.creator_object_boxes, (far,))
            self.assertEqual(load_creator_objects(path), (far,))

    def test_entering_creator_starts_outside_player_head_and_keeps_facing_direction(self):
        level = Level(
            (20, 20), 1, (), (0, settings.PLAYER_EYE_HEIGHT, 0),
            (0, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
            creator_objects_path=Path("creator_objects.json"),
        )
        player = create_player(level, CollisionWorld3D(()))

        player.update(0, InputState(toggle_camera_editor=True))

        eye_position = player.body.eye_position(settings.PLAYER_EYE_HEIGHT)
        self.assertAlmostEqual(player.camera.position.x, eye_position.x, places=5)
        self.assertAlmostEqual(
            player.camera.position.y - eye_position.y, player._CREATOR_ENTRY_HEIGHT, places=5,
        )
        self.assertAlmostEqual(player.camera.position.z, eye_position.z, places=5)
        expected_direction = player._creator_direction()
        actual_direction = glm.normalize(player.camera.target - player.camera.position)
        self.assertLess(glm.length(actual_direction - expected_direction), 1e-5)

    def test_maze_player_uses_fixed_camera_until_leaving_its_zone(self):
        with patch("game.levels.maze.load_fixed_cameras", return_value=None):
            level = create_level("maze")
        world = CollisionWorld3D(
            (box.collider for box in level.boxes), level.floor_bounds,
            ground_height=level.base_height, objects=level.objects,
        )
        player = create_player(level, world)
        self.assertEqual(level.fixed_cameras, ())
        self.assertEqual(player._camera_zones, ())
        initial_target = glm.vec3(player.camera.target)
        player.update(0, InputState())
        player.update(0, InputState(mouse_delta=(120, 80)))
        self.assertEqual(player._active_fixed_camera(), None)
        self.assertNotEqual(tuple(player.camera.target), tuple(initial_target))
        self.assertLess(
            glm.length(player._interaction_camera.position
                       - player.body.eye_position(settings.PLAYER_EYE_HEIGHT)), 1e-5,
        )


if __name__ == "__main__":
    unittest.main()
