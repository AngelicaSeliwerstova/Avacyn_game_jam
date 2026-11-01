from dataclasses import replace
import math
import unittest
from unittest.mock import Mock

import glm

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.navigation.graph import NavigationGraph, PathResult
from engine.scene.box import Box
from engine.scene.level import Level
from game.campaign import Campaign
from game.entities.companion import Companion, CompanionSettings
from game.entities.player import create_player
from game.companions import CompanionSystem
from game.levels.objects import build_objects
from test_hospital import make_body


def fixture(boxes=(), graph=None, objects=(), position=(-4, 0, 0), floor_size=(20, 20)):
    ally = Companion("ally", position, appearance="boxes")
    level = Level(floor_size, 1, boxes, (4, 1.6, 0), (3, 1.6, 0), ((80, 80, 80),) * 2,
                  objects=(ally.scene_object,) + objects, navigation=graph)
    world = CollisionWorld3D((b.collider for b in boxes), level.floor_bounds, objects=level.objects)
    player = create_player(level, world)
    system = CompanionSystem(level, player)
    return ally, player, system


class CompanionTests(unittest.TestCase):
    def test_keeps_up_with_continuous_sprint_at_different_frame_rates(self):
        for fps in (30, 60, 120):
            with self.subTest(fps=fps):
                ally, player, system = fixture(position=(-2, 0, 0), floor_size=(160, 20))
                player.body = make_body(player.body.world, (0, 0, 0))
                for _ in range(fps * 8):
                    player.body.update(1 / fps, glm.vec3(settings.SPRINT_SPEED, 0, 0))
                    system.update(1 / fps)
                self.assertLess(glm.distance(ally.body.position, player.body.position), 2.3)
                for _ in range(fps * 2):
                    player.body.update(1 / fps, glm.vec3(0))
                    system.update(1 / fps)
                self.assertAlmostEqual(glm.distance(ally.body.position, player.body.position),
                                       ally.tuning.stop_distance, places=3)

    def test_catches_up_from_far_away_with_physical_bounded_movement(self):
        ally, player, system = fixture(position=(-20, 0, 0), floor_size=(80, 20))
        for _ in range(240):
            before = ally.body.position
            system.update(1 / 60)
            self.assertLessEqual(glm.distance(before, ally.body.position), ally.tuning.catch_up_speed / 60 + 1e-5)
            self.assertFalse(ally.body.world.is_blocked(ally.body.position, 0.249, 1.799))
        self.assertLess(glm.distance(ally.body.position, player.body.position), 1.5)

    def test_follows_through_security_reception_and_open_stair_lobby(self):
        scene = Campaign().load_level("start")
        system = next(s for s in scene.systems if isinstance(s, CompanionSystem))
        ally = system.companions[0]
        for obj in scene.level.objects:
            if "open" in obj.states:
                obj.set_state("open")
                obj.update(1)
        for goal in ((-3, 0, 7), (11.5, 0, 3.7), (-13, 0, 8.6)):
            with self.subTest(goal=goal):
                scene.player.body = make_body(scene.player.body.world, goal)
                for _ in range(1200):
                    system.update(1 / 30)
                    if math.dist(tuple(ally.body.position), goal) < 1.5:
                        break
                else:
                    self.fail(f"Ally cannot follow reference route to {goal}: {tuple(ally.body.position)}")

    def test_pending_search_is_retargeted_after_player_moves(self):
        ally, player, system = fixture()
        pending = Mock(done=False)
        ally._path_search = pending
        ally._planned_goal = (0, 0, 4)
        ally._planned_revision = ally._navigation.revision
        system.update(1 / 60)
        pending.advance.assert_not_called()
        self.assertIsNone(ally._path_search)
        self.assertEqual(ally._planned_goal, tuple(player.body.position))

    def test_does_not_stop_short_of_old_goal_when_player_is_behind_wall(self):
        wall = Box((0, 1.5, 0), (0.5, 3, 4))
        ally, player, system = fixture((wall,), position=(-1, 0, 1))
        ally._path = [(-1, 0, 2)]
        ally.path_complete = True
        ally._planned_goal = tuple(player.body.position)
        ally._planned_revision = ally._navigation.revision
        ally._path_timer = 1
        system.update(1 / 60)
        self.assertGreater(ally.body.position.z, 1)

    def test_completed_search_does_not_send_moving_companion_backwards(self):
        ally, player, system = fixture(position=(-1, 0, 3))
        ally._path = [(3, 0, 3), (4, 0, 0)]
        ally._planned_goal = tuple(player.body.position)
        ally._planned_revision = ally._navigation.revision
        ally._path_timer = 1
        ally._path_search = Mock(done=True, result=PathResult(
            ((-3, 0, 3), (3, 0, 3), (4, 0, 0)), True))
        before = ally.body.position.x
        system.update(1 / 60)
        self.assertGreater(ally.body.position.x, before)

    def test_hospital_companion_can_leave_open_door_corner(self):
        scene = Campaign().load_level("start")
        system = next(s for s in scene.systems if isinstance(s, CompanionSystem))
        ally = system.companions[0]
        for obj in scene.level.objects:
            if "open" in obj.states:
                obj.set_state("open")
                obj.update(1)
        ally.body = make_body(ally.body.world, (11.675, 9.6, 1.813303))
        goal = (17.5, 0, 2)
        scene.player.body = make_body(scene.player.body.world, goal)
        for _ in range(1800):
            system.update(1 / 30)
            if math.dist(tuple(ally.body.position), goal) < 1.5:
                break
        else:
            self.fail(f"Companion stuck near open door: {tuple(ally.body.position)}")

    def test_player_can_walk_through_companion_without_removing_it_from_scene(self):
        scene = Campaign().load_level("start")
        ally = scene.session.companions[0]

        self.assertIn(ally.scene_object, scene.level.objects)
        self.assertFalse(scene.player.body.world.is_blocked(
            ally.body.position, scene.player.body.radius, scene.player.body.height,
        ))

    def test_follows_stops_near_player_and_resumes_without_jitter(self):
        ally, player, system = fixture()
        for _ in range(180):
            system.update(1 / 60)
        distance = glm.distance(ally.body.position, player.body.position)
        self.assertAlmostEqual(distance, ally.tuning.stop_distance, places=3)
        before = tuple(ally.body.position)
        for _ in range(60):
            system.update(1 / 60)
        self.assertEqual(tuple(ally.body.position), before)
        player.body = make_body(player.body.world, (7, 0, 0))
        for _ in range(180):
            system.update(1 / 60)
        self.assertLess(glm.distance(ally.body.position, player.body.position), 1.5)

    def test_astar_routes_around_wall_without_crossing_it(self):
        wall = Box((0, 1.5, 0), (0.5, 3, 4))
        graph = NavigationGraph(((-3, 0, 0), (-3, 0, 3), (3, 0, 3), (3, 0, 0)),
                                ((0, 1, False), (1, 2, False), (2, 3, False)), connection_distance=4)
        ally, player, system = fixture((wall,), graph)
        farthest_z = 0
        for _ in range(360):
            system.update(1 / 60)
            farthest_z = max(farthest_z, ally.body.position.z)
            self.assertFalse(ally.body.world.is_blocked(ally.body.position, 0.249, 1.799))
        self.assertGreater(farthest_z, 2.25)
        self.assertLess(glm.distance(ally.body.position, player.body.position), 1.5)

    def test_astar_search_can_be_advanced_in_bounded_steps(self):
        graph = NavigationGraph(((-3, 0, 0), (-3, 0, 3), (3, 0, 3), (3, 0, 0)),
                                ((0, 1, False), (1, 2, False), (2, 3, False)), connection_distance=4)
        ally, player, _ = fixture((Box((0, 1.5, 0), (0.5, 3, 4)),), graph)
        search = graph.start_path_search(ally.body.position, player.body.position, ally._navigation)
        self.assertFalse(search.done)
        while not search.done:
            self.assertLessEqual(search.advance(max_expansions=1, max_seconds=0.1), 1)
        self.assertTrue(search.result.complete)
        self.assertGreater(len(search.result.points), 2)

    def test_replans_when_closed_door_opens(self):
        doors = build_objects([{"id": "door", "type": "door", "position": (0, 0, 0),
                                "axis": "z", "opening_width": 3, "width": 1.8}])
        wall = (Box((0, 1.5, -5.75), (0.4, 3, 8.5)), Box((0, 1.5, 5.75), (0.4, 3, 8.5)))
        ally, player, system = fixture(wall, objects=doors)
        for _ in range(120):
            system.update(1 / 60)
        self.assertLess(ally.body.position.x, 0)
        door = next(o for o in doors if o.name == "door")
        door.set_state("open")
        door.update(1)
        for _ in range(180):
            system.update(1 / 60)
        self.assertLess(glm.distance(ally.body.position, player.body.position), 1.5)

    def test_replans_when_obstacle_is_added_to_current_route(self):
        graph = NavigationGraph(((-3, 0, 0), (-3, 0, 3), (3, 0, 3), (3, 0, 0)),
                                ((0, 1, False), (1, 2, False), (2, 3, False)), connection_distance=4)
        ally, player, system = fixture(graph=graph)
        for _ in range(20):
            system.update(1 / 60)
        player._creator_objects = (Box((0, 1.5, 0), (0.5, 3, 4)),)
        farthest_z = 0
        for _ in range(360):
            system.update(1 / 60)
            farthest_z = max(farthest_z, ally.body.position.z)
        self.assertGreater(farthest_z, 2.25)
        self.assertLess(glm.distance(ally.body.position, player.body.position), 1.5)

    def test_conversation_is_required_before_world_transition(self):
        from support_story import finish_conversation
        campaign = Campaign()
        scene = campaign.load_level("peaceful")
        scene.session.tick_presentation(4)
        ally = scene.session.companions[0]
        self.assertFalse(ally.following)
        self.assertNotEqual(ally.model, scene.player.model)
        self.assertEqual(ally.model.source_path.name, "girl_white.glb")
        self.assertTrue(ally.model.source_path.is_file())
        self.assertEqual(ally.scene_object.render_boxes, ())
        scene.session.update(0)
        self.assertIsNone(scene.session.next_level)
        scene.player._interactions._activate(ally.scene_object)
        scene.session.update(0)
        self.assertIsNone(scene.session.next_level)
        finish_conversation(scene.session)
        self.assertIsNone(scene.session.next_level)
        scene.session.tick_presentation(4)
        self.assertEqual(scene.session.next_level, "start")
        self.assertIn("recruited:hospital_companion", campaign.progress.flags)
        horror = campaign.load_level(scene.session.next_level)
        self.assertTrue(horror.session.companions[0].following)

    def test_companion_can_follow_up_and_down_both_spiral_flights(self):
        scene = Campaign().load_level("start")
        system = next(s for s in scene.systems if isinstance(s, CompanionSystem))
        ally = system.companions[0]
        ally.body = make_body(ally.body.world, (-13, 0, 8.6))
        for goal in ((-7, 9.6, 6.9), (-13, 0, 8.6)):
            scene.player.body = make_body(scene.player.body.world, goal)
            for frame in range(1800):
                system.update(1 / 30)
                if glm.distance(ally.body.position, glm.vec3(goal)) < 1.5:
                    break
            else:
                self.fail(f"Companion stuck at {tuple(ally.body.position)} following {goal}; path={ally.remaining_path}")
            self.assertAlmostEqual(ally.body.position.y, goal[1], places=3)

    def test_invalid_settings_are_rejected(self):
        for data in ({"speed": 0}, {"stop_distance": 0}, {"resume_distance": 1}, {"speed": math.nan},
                     {"catch_up_speed": 0}, {"catch_up_speed": math.inf}):
            with self.assertRaises(ValueError):
                CompanionSettings(**data)

    def test_hospital_companion_leaves_office_and_routes_to_stair_hall(self):
        scene = Campaign().load_level("start")
        system = next(s for s in scene.systems if isinstance(s, CompanionSystem))
        ally = system.companions[0]
        for obj in scene.level.objects:
            if "open" in obj.states:
                obj.set_state("open")
                obj.update(1)
        goal = (-13, 0, 8.6)
        scene.player.body = make_body(scene.player.body.world, goal)
        for _ in range(1200):
            system.update(1 / 30)
            if glm.distance(ally.body.position, glm.vec3(goal)) < 1.5:
                break
        else:
            self.fail(f"Office route blocked: {tuple(ally.body.position)}, path={ally.remaining_path}")
