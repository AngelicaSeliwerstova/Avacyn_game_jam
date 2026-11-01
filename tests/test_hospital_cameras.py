"""Gameplay checks for the authored hospital shots, using real collision geometry."""
import unittest
from unittest.mock import patch

import glm

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.input.state import InputState
from game.entities.player import create_player
from game.levels import create_level
from game.levels.spiral import SpiralStair


def player_for(name, open_doors=False):
    level = create_level(name)
    if open_doors:
        for obj in level.objects:
            if "open" in obj.states:
                obj.set_state("open")
                obj.update(2)
    world = CollisionWorld3D((b.collider for b in level.collision_boxes), level.floor_bounds,
                             level.base_height, objects=tuple(o for o in level.objects if o.entity is None))
    return level, create_player(level, world)


class HospitalCameraTests(unittest.TestCase):
    def test_all_campaign_entries_have_a_clear_fixed_shot_and_unembedded_lenses(self):
        for name in ("peaceful", "start", "act1", "act2"):
            with self.subTest(level=name):
                level, player = player_for(name)
                self.assertTrue(level.fixed_cameras_authored)
                zone = player._active_fixed_camera()
                self.assertIsNotNone(zone)
                self.assertIsNotNone(player._fixed_camera_framing_score(zone, player._player_eye_position()))
                for index, camera in enumerate(level.fixed_cameras):
                    lens = player._camera_view_position(camera)
                    self.assertFalse(player.body.world.is_blocked(lens, .04, .08), (name, index))

    def test_walkable_grid_has_visible_shots_in_both_worlds(self):
        for name in ("peaceful", "start"):
            level, player = player_for(name, open_doors=True)
            world = player.body.world
            for floor, height in enumerate(level.floor_heights):
                width, depth = (42, 28) if floor == 0 else (60, 48)
                for x in range(-width // 2 + 1, width // 2, 3):
                    for z in range(-depth // 2 + 1, depth // 2, 3):
                        point = glm.vec3(x, height + .03, z)
                        if world.is_blocked(point, settings.PLAYER_RADIUS, player.body.height):
                            continue
                        if abs(world.support_height(point, settings.PLAYER_RADIUS, height + .08) - height) > .08:
                            continue
                        player.body._position = glm.vec3(x, height, z)
                        player._active_camera_zone = None
                        zone = player._active_fixed_camera()
                        self.assertIsNotNone(player._fixed_camera_framing_score(
                            zone, player._player_eye_position()), (name, x, height, z))

    def test_both_stair_flights_remain_visible_ascending_and_descending(self):
        _, player = player_for("start", open_doors=True)
        path = SpiralStair().walking_path()
        player._movement_camera_lock = True
        for points in (path, path[::-1]):
            for point in points:
                player.body._position = glm.vec3(point)
                zone = player._active_fixed_camera()
                self.assertIsNotNone(player._fixed_camera_framing_score(
                    zone, player._player_eye_position()), point)

    def test_closed_doors_are_visible_from_both_reachable_sides(self):
        level, player = player_for("start")
        for obj in level.objects:
            if "open" not in obj.states:
                continue
            panel = obj.states["default"].boxes[0]
            x, y, z = panel.position
            height = y - panel.size[1] / 2 - .02
            for sign in (-1, 1):
                point = (x, height, z + sign * 1.5) if panel.size[0] > panel.size[2] else (
                    x + sign * 1.5, height, z)
                if player.body.world.is_blocked(glm.vec3(point) + glm.vec3(0, .02, 0), .24, player.body.height):
                    continue
                player.body._position = glm.vec3(point)
                player._active_camera_zone = None
                player._sync_fixed_camera()
                self.assertIsNotNone(player._interactions._visible_score(
                    player.camera, tuple(player.camera.position), panel.collider, obj), (obj.name, point))

    def test_archive_and_act_one_clues_are_visible_from_interaction_distance(self):
        level, player = player_for("act1")
        checks = {
            "hospital_plan": (13.4, 0, 2.3),
            "mother_letter": (11.6, 0, 7.4),
            "security_archive": (-1.8, 0, 3.2),
            "f3_ward_305_clock": (5, 9.6, -21.8),
            "f3_ward_306_tv": (11, 9.6, -20.7),
            "f3_ward_307_toy": (16.2, 9.6, -21.5),
            "f3_ward_308_drawing": (27.8, 9.6, -13.2),
        }
        for name, point in checks.items():
            obj = next(o for o in level.objects if o.name == name)
            box = obj.current_state.selection_box or obj.boxes[0]
            player.body._position = glm.vec3(point)
            player._active_camera_zone = None
            player._sync_fixed_camera()
            self.assertLessEqual(player._interactions._surface_distance(
                tuple(player._player_eye_position()), box.collider), settings.INTERACTION_REACH)
            self.assertIsNotNone(player._interactions._visible_score(
                player.camera, tuple(player.camera.position), box.collider, obj), name)

    def test_retaining_shot_does_not_raycast_all_hospital_cameras(self):
        _, player = player_for("start")
        player._active_fixed_camera()
        with patch.object(player, "_fixed_camera_framing_score",
                          wraps=player._fixed_camera_framing_score) as score:
            player._active_fixed_camera()
        self.assertEqual(score.call_count, 1)

    def test_documents_and_terminal_can_be_selected_after_arriving_from_hall(self):
        routes = {
            "hospital_plan": ((11.5, 0, 8), (19.4, 0, 9.5), (19.4, 0, 2.6),
                              (17, 0, 2.6), (13.4, 0, 2.3)),
            "security_archive": ((-3, 0, -1.5), (-3, 0, .8), (-1.8, 0, 3.2)),
        }
        for name, points in routes.items():
            _, player = player_for("start", open_doors=True)
            # Keep the previous camera and movement lock while crossing zones;
            # resetting the camera at each sample would miss arrival problems.
            for point in points:
                player.body._position = glm.vec3(point)
                player.update(0, InputState(forward=1))
            player.update(0, InputState())
            self.assertEqual(getattr(player._interactions.focused, "name", None), name)


if __name__ == "__main__":
    unittest.main()
