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

    def test_overlapping_camera_zones_keep_camera_while_its_frame_still_covers_player(self):
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
        self.assertIs(player._active_fixed_camera(), first)

    def test_camera_selection_uses_player_eye_height_when_testing_camera_framing(self):
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
        self.assertIs(player._active_fixed_camera(), first)

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

    def test_camera_layout_round_trips_and_model_led_flashes(self):
        zone = FixedCameraZone(
            minimum=(-1, 0, -1), maximum=(1, 3, 1),
            position=(0, 2, 0), target=(0, 1, -2),
        )
        on = camera_model_boxes(zone, True)
        off = camera_model_boxes(zone, False)
        self.assertEqual(len(on), 13)
        self.assertNotEqual(on[9].emission, off[9].emission)
        self.assertEqual(on[7].color, (0.025, 0.09, 0.14))
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

    def test_authored_cameras_keep_automatic_maze_coverage(self):
        authored = FixedCameraZone(
            minimum=(-1, -1, -1), maximum=(1, 3, 1),
            position=(0, 2, 0), target=(0, 2, -4),
        )
        with patch("game.levels.maze.load_fixed_cameras", return_value=(authored,)):
            level = create_level("maze")
        self.assertEqual(level.authored_fixed_cameras, (authored,))
        self.assertEqual(level.fixed_cameras[0], authored)
        self.assertGreater(len(level.fixed_cameras), 300)

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

            player.update(0, InputState(delete_camera=True))
            self.assertEqual(load_creator_objects(path), ())

    def test_maze_player_uses_fixed_camera_until_leaving_its_zone(self):
        with patch("game.levels.maze.load_fixed_cameras", return_value=None):
            level = create_level("maze")
        world = CollisionWorld3D(
            (box.collider for box in level.boxes), level.floor_bounds,
            ground_height=level.base_height, objects=level.objects,
        )
        player = create_player(level, world)
        zone = next(camera for camera in level.fixed_cameras if camera.contains(tuple(player.body.position)))

        player.update(0, InputState())
        position, target = tuple(player.camera.position), tuple(player.camera.target)
        self.assertLess(glm.length(player.camera.position - glm.vec3(zone.position)), 1e-5)
        self.assertLess(glm.length(player.camera.target - glm.vec3(zone.target)), 1e-5)
        player.update(0, InputState(mouse_delta=(120, 80)))
        self.assertEqual(tuple(player.camera.position), position)
        self.assertEqual(tuple(player.camera.target), target)
        self.assertLess(
            glm.length(player._interaction_camera.position
                       - player.body.eye_position(settings.PLAYER_EYE_HEIGHT)), 1e-5,
        )
        self.assertGreater(len(level.fixed_cameras), 300)

        for other_zone in level.fixed_cameras:
            if other_zone.position == zone.position:
                continue
            x = (other_zone.minimum[0] + other_zone.maximum[0]) / 2
            y = other_zone.minimum[1] + 0.15
            z = (other_zone.minimum[2] + other_zone.maximum[2]) / 2
            if world.is_blocked(glm.vec3(x, y, z), player.body.radius, player.body.height):
                continue
            other_level = replace(
                level, spawn_position=(x, y + settings.PLAYER_EYE_HEIGHT, z),
                spawn_target=(x, y + settings.PLAYER_EYE_HEIGHT, z - 1),
            )
            other_player = create_player(other_level, world)
            other_player.update(0, InputState())
            self.assertLess(glm.length(other_player.camera.position - glm.vec3(other_zone.position)), 1e-5)
            break
        else:
            self.fail("Maze has no second unblocked fixed-camera zone")


if __name__ == "__main__":
    unittest.main()
