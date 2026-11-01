"""Act 1 progression uses the real objects, collision world and editable script."""
from unittest.mock import Mock, patch
import unittest

import glm

from config import settings
from engine.scene.camera import Camera, FixedCameraZone
from game.campaign import Campaign
from game.companions import CompanionSystem
from game.hospital_audio import HospitalAudioSystem
from game.levels.cameras import camera_model_boxes
from game.levels.hospital_story import CHILD_BED_TARGET, CHILD_CAMERAS
from game.levels.story_props import StoryPropSystem
from support_story import finish_conversation
from test_hospital import make_body, walk


class ActOneTests(unittest.TestCase):
    def setUp(self):
        self.audio = patch.object(settings, "AUDIO_ENABLED", False)
        self.audio.start()
        self.addCleanup(self.audio.stop)

    def begin(self, choice=0):
        scene = Campaign().load_level("act1")
        session = scene.session
        self.assertEqual(session.act.id, "act1")
        self.assertEqual(session.dialog.presentation, "title")
        session.tick_presentation(4)
        finish_conversation(session, choice)
        self.assertTrue(session.actors["doctor"].following)
        self.assertEqual(len(scene.player.inventory.items), 2)
        return scene

    def obj(self, scene, name):
        return next(o for o in scene.level.objects if o.name == name)

    def interact(self, scene, name, position):
        """Check physical reach and visibility, then press the actual action."""
        player = scene.player
        player.body._position = glm.vec3(position)
        self.assertFalse(player.body.world.is_blocked(player.body.position, player.body.radius, player.body.height))
        obj = self.obj(scene, name)
        box = obj.current_state.selection_box or obj.boxes[0]
        eye = tuple(player.body.eye_position(settings.PLAYER_EYE_HEIGHT))
        camera = Camera(eye, box.position, 65, 0.1, 150)
        player._interactions.update(0, camera, reach_origin=eye)
        self.assertIs(player._interactions.focused, obj, name)
        player._interactions.update(0, camera, pressed=True, reach_origin=eye)
        scene.session.update(0)
        return obj

    def start_music(self, scene, choice=0):
        door = self.interact(scene, "f3_patient_ward_313", (14.5, 9.6, 5))
        self.assertEqual(door.state_name, "default")
        self.assertNotIn("act1:music", scene.session._flags)
        finish_conversation(scene.session, choice)
        self.assertIn("act1:music", scene.session._flags)

    def enter_child_room(self, scene, choice=0):
        session = scene.session
        self.interact(scene, "f3_patient_room_7", (24.5, 9.6, -8.4)).update(1)
        walk(self, scene.player.body, ((24.5, 9.6, -13), (26, 9.6, -15.5)), fps=20)
        self.interact(scene, "f3_patient_child_room", (26, 9.6, -15.5)).update(1)
        walk(self, scene.player.body, ((26, 9.6, -18.5),), fps=20)
        session.update(0)
        finish_conversation(session, choice)
        key = self.obj(scene, "f3_ward_313_key")
        self.assertIsNone(key.interaction)
        self.assertTrue(session.controls_locked)
        self.assertFalse(session.handle_gameplay_key("m"))
        self.assertIn("act1:music_muted", session._flags)
        session.update(1.5)
        finish_conversation(session, choice)
        self.assertFalse(session.controls_locked)
        self.assertIsNotNone(key.interaction)
        self.assertNotIn("act1:music_muted", session._flags)

    def test_all_response_branches_reach_key_memory_and_slow_door_ending(self):
        for choice in range(3):
            with self.subTest(choice=choice):
                scene = self.begin(choice)
                session = scene.session
                self.start_music(scene, choice)
                # The staircase route is covered separately; begin at its upper landing.
                scene.player.body._position = glm.vec3(-7, 9.6, 6.9)
                walk(self, scene.player.body, ((12, 9.6, 6.9), (12, 9.6, -7.5),
                                             (24.5, 9.6, -7.5)), fps=20)
                self.enter_child_room(scene, choice)
                self.interact(scene, "f3_ward_313_key", (26, 9.6, -18.8))
                self.assertEqual(session.dialog.presentation, "memory")
                self.assertEqual(session.dialog.title, "Голос девочки")
                finish_conversation(session, choice)
                self.assertIn("act1:memory_done", session._flags)
                self.assertTrue(scene.player.inventory.has_key("ward_313"))
                self.assertEqual(self.obj(scene, "f3_ward_313_key").state_name, "collected")
                walk(self, scene.player.body, ((26, 9.6, -15),), fps=20)
                session.update(0)
                self.assertEqual(session.dialog.message, session.act.dialogues["return"][0]["text"])
                finish_conversation(session, choice)
                walk(self, scene.player.body, ((24.5, 9.6, -13), (24.5, 9.6, -7.5),
                                             (12, 9.6, -7.5), (12, 9.6, 5), (14.5, 9.6, 5)), fps=20)
                door = self.interact(scene, "f3_patient_ward_313", (14.5, 9.6, 5))
                self.assertTrue(session.controls_locked)
                self.assertFalse(session.handle_gameplay_key("m"))
                door.update(0.5)
                session.update(0.5)
                self.assertIsNone(session.dialog)
                self.assertNotIn("act1:complete", session._flags)
                door.update(1.1)
                session.update(1.1)
                self.assertEqual(session.dialog.presentation, "blackout")
                session.tick_presentation(0.75)
                self.assertAlmostEqual(session.dialog.opacity, 0.5)
                session.tick_presentation(0.75)
                self.assertIn("act1:complete", session._flags)
                self.assertEqual(session.dialog.presentation, "ending")
                self.assertEqual(session.dialog.title, "КОНЕЦ АКТА 1")
                for name in ("route", "melody", "first_memory", "own_memory"):
                    self.assertIn(f"act1:choice:{name}:{choice}", session._flags)
                self.assertLess(scene.player.body.position.x, 16)
                scene.session.release()

    def test_optional_rooms_reachable_and_tv_flash_returns_to_static(self):
        scene = self.begin()
        self.start_music(scene)
        session = scene.session
        for room, prop, position in ((4, "ward_305_clock", (5, 9.6, -21.6)),
                                     (5, "ward_306_tv", (11, 9.6, -20.5)),
                                     (6, "ward_307_toy", (16, 9.6, -21.3)),
                                     (7, "ward_308_drawing", (28.5, 9.6, -13.2))):
            door = self.obj(scene, f"f3_patient_room_{room}")
            door.set_state("open")
            door.update(1)
            x = door.states["default"].boxes[0].position[0]
            scene.player.body._position = glm.vec3(x, 9.6, -8)
            walk(self, scene.player.body, ((x, 9.6, -12), (x, 9.6, position[2]), position), fps=20)
            obj = self.interact(scene, "f3_" + prop, position)
            if room == 5:
                self.assertEqual(obj.state_name, "memory")
                self.assertTrue(session.controls_locked)
                session.update(0.5)
                self.assertEqual(obj.state_name, "memory")
                session.update(0.5)
                self.assertEqual(obj.state_name, "default")
                self.assertFalse(session.controls_locked)
                shadows = scene.level.static_shadow_boxes
                StoryPropSystem(scene.level).update(0.15)
                self.assertEqual(obj.state_name, "noise")
                self.assertEqual(scene.level.static_shadow_boxes, shadows)
            finish_conversation(session, 2)
            self.assertIsNone(session.dialog)
        self.assertIn("act1:choice:television:2", session._flags)
        self.assertNotIn("act1:key_taken", session._flags)

    def test_stair_comment_survives_act_transition_and_is_only_said_once(self):
        scene = self.begin()
        session = scene.session
        scene.player.story_events.add("stairs_walk_finished")
        session.update(0)
        self.assertIn("Меня в дрожь бросает от лестниц", scene.player.story_status)
        session.update(8)
        scene.player.story_events.add("stairs_walk_finished")
        session.update(0)
        self.assertEqual(scene.player.story_status, "")

    def test_music_guides_by_distance_and_stops_for_key_and_silence(self):
        scene = self.begin()
        self.start_music(scene)
        sounds = Mock()
        system = HospitalAudioSystem(scene.level, scene.player, scene.session, sounds=sounds)
        source = next(s for s in system._story_sources if s["id"] == "music_box")
        levels = []
        with patch.object(settings, "AUDIO_ENABLED", True):
            for x in (5, 11, 17.5, 25):
                scene.player.body._position = glm.vec3(x, 9.6, -20)
                levels.append(sum(system._stereo(source["position"], source["volume"], source["radius"])))
            self.assertEqual(levels, sorted(levels))
            self.assertGreater(levels[-1], levels[0] * 3)
            scene.player.body._position.y = 4.8
            self.assertLess(sum(system._stereo(source["position"], source["volume"], source["radius"])), levels[-1] * 0.12)
            scene.player.body._position.y = 9.6
            system.update(0)
            self.assertIn(source["sound"], [call.args[1] for call in sounds.loop.call_args_list])
            scene.session._flags.add("act1:music_muted")
            system.set_paused(True)
            sounds.stop_loop.assert_any_call(source["slot"])
            scene.session._flags.remove("act1:music_muted")
            scene.session._flags.add("act1:key_taken")
            sounds.reset_mock()
            system.set_paused(False)
            self.assertNotIn(source["sound"], [call.args[1] for call in sounds.loop.call_args_list])

    def test_every_child_camera_model_points_down_at_the_bed(self):
        for position in CHILD_CAMERAS:
            camera = FixedCameraZone((21, 0, -24), (30, 4.56, -17), position, CHILD_BED_TARGET)
            body = camera_model_boxes(camera, True, aim_pitch=True)[3]
            forward = glm.quat(*body.orientation) * glm.vec3(0, 0, -1)
            target = glm.normalize(glm.vec3(CHILD_BED_TARGET) - glm.vec3(position))
            self.assertGreater(glm.dot(forward, target), 0.99999)

    def test_doctor_follows_into_child_room_and_back_to_313(self):
        scene = self.begin()
        system = next(s for s in scene.systems if isinstance(s, CompanionSystem))
        doctor = system.companions[0]
        doctor.body = make_body(scene.player.body.world, (12, 9.6, 5))
        for name in ("f3_patient_room_7", "f3_patient_child_room"):
            door = self.obj(scene, name)
            door.set_state("open")
            door.update(1)
        for goal in ((26, 9.6, -18.6), (14, 9.6, 5)):
            scene.player.body = make_body(scene.player.body.world, goal)
            for _ in range(1000):
                system.update(1 / 20)
                if glm.distance(doctor.body.position, glm.vec3(goal)) < 1.6:
                    break
            else:
                self.fail(f"Doctor failed to reach {goal}: {doctor.body.position}")


if __name__ == "__main__":
    unittest.main()
