from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import wave

import glm

from game.footsteps import FootstepSystem


def actor(position=(0, 0, 0)):
    return SimpleNamespace(body=SimpleNamespace(position=glm.vec3(position), grounded=True,
                           horizontal_speed=3.5, height=1.8, standing_height=1.8),
                           creator_mode=False, camera=SimpleNamespace(position=glm.vec3(0, 1.6, 0),
                                                                    target=glm.vec3(0, 1.6, -1)))


class FootstepTests(unittest.TestCase):
    def make_system(self):
        player, sounds = actor(), Mock()
        return FootstepSystem(SimpleNamespace(objects=()), player, sounds), player, sounds

    def test_actual_motion_triggers_single_steps_and_cadence_is_frame_rate_independent(self):
        counts = []
        for fps in (30, 60, 120):
            system, player, sounds = self.make_system()
            for _ in range(fps * 4):
                player.body.position.x += 3.5 / fps
                system.update(1 / fps)
            counts.append(sounds.play.call_count)
            self.assertTrue(all(call.args[0] == "player" for call in sounds.play.call_args_list))
        self.assertLessEqual(max(counts) - min(counts), 1)
        self.assertGreaterEqual(min(counts), 8)

    def test_stationary_airborne_and_creator_do_not_play_and_pause_stops_tails(self):
        system, player, sounds = self.make_system()
        for _ in range(60):
            system.update(1 / 60)
        sounds.play.assert_not_called()
        player.body.grounded = False
        for _ in range(60):
            player.body.position.x += 0.06
            system.update(1 / 60)
        player.body.grounded = True
        player.creator_mode = True
        for _ in range(60):
            player.body.position.x += 0.06
            system.update(1 / 60)
        sounds.play.assert_not_called()
        system.set_paused(True)
        sounds.stop.assert_called_once()

    def test_doctor_is_spatial_and_fades_with_distance_and_between_floors(self):
        system, _, _ = self.make_system()
        doctor = actor((3, 0, 0))
        left, right = system._stereo(doctor, 0.7)
        self.assertGreater(right, left)
        doctor.body.position = glm.vec3(-3, 0, 0)
        left, right = system._stereo(doctor, 0.7)
        self.assertGreater(left, right)
        doctor.body.position = glm.vec3(0, 0, -3)
        near = sum(system._stereo(doctor, 0.7))
        doctor.body.position.y = 4.8
        self.assertLess(sum(system._stereo(doctor, 0.7)), near * 0.25)
        doctor.body.position = glm.vec3(30, 0, 0)
        self.assertEqual(system._stereo(doctor, 0.7), (0, 0))

    def test_pack_contains_eight_short_pcm_steps(self):
        root = Path(__file__).resolve().parents[1] / "resources/audio/footsteps"
        for profile in ("player", "doctor"):
            for index in range(1, 5):
                with wave.open(str(root / f"{profile}_step_{index:02}.wav")) as clip:
                    self.assertEqual((clip.getnchannels(), clip.getsampwidth(), clip.getframerate()), (1, 2, 44100))
                    duration = clip.getnframes() / clip.getframerate()
                    self.assertTrue(0.2 <= duration <= 0.55)
