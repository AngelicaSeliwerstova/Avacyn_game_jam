from array import array
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import random
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import wave

import glm
import pygame

from config import settings
from engine.scene.session import Dialog
from game.campaign import Campaign
from game.hospital_audio import AUDIO_ROOT, CONFIG_PATH, HospitalAudioSystem, HospitalSoundBank, load_audio_profile
from game.levels.objects import build_objects
from test_footsteps import actor


class HospitalAudioTests(unittest.TestCase):
    def system(self, profile="abandoned"):
        player, sounds = actor(), Mock()
        doors = build_objects(({"id": "door", "type": "door", "position": (3, 0, 0)},))
        level = SimpleNamespace(objects=doors, audio_profile=profile)
        session = SimpleNamespace(dialog=None)
        system = HospitalAudioSystem(level, player, session, sounds=sounds, rng=random.Random(1))
        return system, player, sounds, doors[-1]

    def test_levels_select_different_backgrounds_without_initializing_the_mixer(self):
        with patch("pygame.mixer.init") as initialize:
            peaceful = Campaign().load_level("peaceful")
            abandoned = Campaign().load_level("start")
        initialize.assert_not_called()
        first = next(s for s in peaceful.systems if isinstance(s, HospitalAudioSystem))
        second = next(s for s in abandoned.systems if isinstance(s, HospitalAudioSystem))
        self.assertIn("activity", {loop["sound"] for loop in first.profile["loops"]})
        self.assertNotIn("activity", {loop["sound"] for loop in second.profile["loops"]})

    def test_pause_ducks_background_and_transformation_reaches_silence(self):
        system, _, sounds, _ = self.system()
        system.update(0.1)
        normal = sounds.loop.call_args.args[-1]
        system.session.dialog = Dialog("Doctor", "Line", (), presentation="conversation")
        system.set_paused(True)
        self.assertAlmostEqual(sounds.loop.call_args.args[-1], normal * settings.AMBIENCE_DIALOGUE_GAIN)
        system.session.dialog = Dialog("", "", (), presentation="interference", effect_time=0.6)
        system.set_paused(True)
        self.assertAlmostEqual(sounds.loop.call_args.args[-1], normal * 0.5)
        system.session.dialog = Dialog("", "", (), presentation="blackout")
        system.set_paused(True)
        self.assertEqual(sounds.loop.call_args.args[-1], 0)
        self.assertEqual(sounds.duck_effects.call_args.args[0], 0)
        system.session.dialog = None
        system.set_paused(False)
        self.assertAlmostEqual(sounds.loop.call_args.args[-1], normal)

    def test_door_only_sounds_on_open_close_and_mute_or_creator_suppress_effects(self):
        system, player, sounds, door = self.system()
        system.update(0)
        sounds.play.assert_not_called()
        door.set_state("open")
        system.update(0)
        self.assertEqual(sounds.play.call_args.args[0], "creak")
        self.assertGreater(max(sounds.play.call_args.args[1:]), 0)
        count = sounds.play.call_count
        system.update(0.1)
        self.assertEqual(sounds.play.call_count, count)
        door.update(1)
        door.set_state("default")
        system.update(0)
        self.assertEqual(sounds.play.call_count, count + 1)
        with patch.object(settings, "AUDIO_ENABLED", False):
            door.set_state("open")
            system.update(0)
            self.assertEqual(sounds.play.call_count, count + 1)
        player.creator_mode = True
        system.set_paused(True)
        sounds.stop_effects.assert_called()
        self.assertEqual(sounds.loop.call_args.args[-1], 0)

    def test_equipment_is_directional_distance_limited_and_muffled_between_floors(self):
        system, _, _, _ = self.system()
        left, right = system._stereo((3, 1, 0), 1, 12)
        self.assertGreater(right, left)
        self.assertGreater(system._stereo((-3, 1, 0), 1, 12)[0], right * 0.9)
        self.assertEqual(system._stereo((20, 0, 0), 1, 12), (0, 0))
        upper = sum(system._stereo((3, 5.8, 0), 1, 12))
        self.assertLess(upper, (left + right) * 0.12)

    def test_equipment_timers_do_not_burst_after_a_pause(self):
        system, player, sounds, _ = self.system("peaceful")
        player.body.position = glm.vec3(-10, 0, -10)
        system._emitter_timers[0] = 0
        system.update(0.1)
        self.assertEqual(sounds.play.call_args.args[0], "monitor")
        self.assertGreater(max(sounds.play.call_args.args[1:]), 0)
        count = sounds.play.call_count
        system.set_paused(True)
        system.update(100)
        self.assertEqual(sounds.play.call_count, count)
        system.set_paused(False)
        system.update(0.1)
        self.assertEqual(sounds.play.call_count, count)

    def test_release_stops_everything_and_cannot_restart_old_background(self):
        system, _, sounds, _ = self.system()
        system.update(0.1)
        system.release()
        sounds.stop.assert_called_once()
        sounds.reset_mock()
        system.update(1)
        system.set_paused(False)
        sounds.loop.assert_not_called()
        sounds.play.assert_not_called()

    def test_processed_audio_matches_provenance_and_has_safe_pcm_levels(self):
        manifest = json.loads((AUDIO_ROOT / "hospital/sources.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest), 6)
        for item in manifest:
            with self.subTest(sound=item["id"]):
                path = AUDIO_ROOT / "hospital" / item["file"]
                self.assertEqual(item["license"], "CC0-1.0")
                self.assertTrue(item["url"].startswith("https://freesound.org/people/"))
                self.assertEqual(sha256(path.read_bytes()).hexdigest(), item["sha256"])
                with wave.open(str(path), "rb") as clip:
                    self.assertEqual((clip.getnchannels(), clip.getsampwidth(), clip.getframerate()), (1, 2, 44100))
                    samples = array("h", clip.readframes(clip.getnframes()))
                    self.assertAlmostEqual(len(samples) / 44100, item["duration"])
                self.assertLessEqual(max(abs(sample) for sample in samples), 20316)
                self.assertGreater(math.sqrt(sum(sample * sample for sample in samples) / len(samples)), 200)
                if item["crossfade"]:
                    # Seam discontinuity should be within normal sample-to-sample motion.
                    jumps = sorted(abs(samples[i + 1] - samples[i]) for i in range(0, len(samples) - 1, 20))
                    self.assertLessEqual(abs(samples[0] - samples[-1]), max(5, jumps[int(len(jumps) * 0.99)] * 2))

    def test_invalid_profile_volume_fails_with_file_and_field(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ambience.json"
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            data["profiles"]["peaceful"]["loops"][0]["volume"] = 2
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "loops.*volume"):
                load_audio_profile("peaceful", path)

    def test_missing_audio_device_is_nonfatal(self):
        bank = HospitalSoundBank(load_audio_profile("peaceful")[0])
        with patch("pygame.get_init", return_value=True), patch("pygame.mixer.get_init", return_value=None), \
                patch("pygame.mixer.init", side_effect=pygame.error("no device")):
            bank.loop(0, "room_tone", 0.1, 0.1)
            bank.play("creak", 0.1, 0.1)
            bank.stop()

    def test_breathing_follows_stair_stress_and_stops_for_dialogue_creator_and_rest(self):
        system, player, sounds, _ = self.system()
        system.update(0.1)
        self.assertNotIn("breathing", [call.args[1] for call in sounds.loop.call_args_list])
        player.stair_stress_strength = 0.8
        system.update(0.1)
        self.assertEqual(sounds.loop.call_args.args[0:2], (3, "breathing"))
        high = sounds.loop.call_args.args[-1]
        player.stair_stress_strength = 0.4
        system.update(0.1)
        self.assertAlmostEqual(sounds.loop.call_args.args[-1], high / 2)
        system.set_paused(True)
        sounds.stop_loop.assert_called_with(3)
        system.set_paused(False)
        self.assertEqual(sounds.loop.call_args.args[0:2], (3, "breathing"))
        player.creator_mode = True
        system.set_paused(True)
        sounds.stop_loop.assert_called_with(3)
        player.creator_mode = False
        player.stair_stress_strength = 0
        system.set_paused(False)
        sounds.stop_loop.assert_called_with(3)


if __name__ == "__main__":
    unittest.main()
