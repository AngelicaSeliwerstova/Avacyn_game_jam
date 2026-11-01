from array import array
from hashlib import sha256
import json
import math
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import wave

import glm
import pygame

from config import settings
from engine.scene.box import Box
from engine.scene.camera import Camera
from game.audio_channels import DISCOVERY_CHANNEL, MUSIC_CHANNEL, FIRST_FOOTSTEP_CHANNEL
from game.campaign import Campaign
from game.hospital_audio import AUDIO_ROOT, HospitalAudioSystem, HospitalSoundBank, load_audio_profile
from game.levels.stair_blood import StairBloodDiscovery
from test_footsteps import actor


class MusicTests(unittest.TestCase):
    def system(self, flags=None, profile="abandoned"):
        player, sounds = actor(), Mock()
        player.camera = Camera((0, 1.6, 0), (0, 0, -5), 60, 0.1, 100)
        player.body.world = SimpleNamespace(colliders=())
        session = SimpleNamespace(dialog=None, _flags=flags if flags is not None else set())
        level = SimpleNamespace(objects=(), audio_profile=profile, stair_blood_targets=((0, 0.02, -5),))
        return HospitalAudioSystem(level, player, session, sounds=sounds), player, sounds

    def test_music_uses_reserved_channel_ducks_for_dialogue_and_stops_on_release(self):
        system, _, sounds = self.system()
        system._blood.targets = ()
        system.update(0)
        music = next(c for c in sounds.loop.call_args_list if c.args[0] == MUSIC_CHANNEL)
        self.assertEqual(music.args[1], "hospital_music")
        sounds.reset_mock()
        system.set_paused(True)
        quiet = next(c for c in sounds.loop.call_args_list if c.args[0] == MUSIC_CHANNEL)
        self.assertAlmostEqual(quiet.args[2], music.args[2] * settings.AMBIENCE_DIALOGUE_GAIN)
        system.release()
        sounds.stop.assert_called_once()
        peaceful, _, quiet_sounds = self.system(profile="peaceful")
        peaceful.update(0)
        self.assertNotIn(MUSIC_CHANNEL, [c.args[0] for c in quiet_sounds.loop.call_args_list])
        quiet_sounds.play_discovery.assert_not_called()

    def test_discovery_requires_camera_view_clear_line_of_sight_and_nearby_pool(self):
        system, player, sounds = self.system()
        player.camera.target = glm.vec3(0, 1.6, 5)
        system.update(0)
        sounds.play_discovery.assert_not_called()
        player.camera.target = glm.vec3(0, 0, -5)
        player.body.world.colliders = (Box((0, 1, -2), (4, 3, 0.2)).collider,)
        system.update(0)
        sounds.play_discovery.assert_not_called()
        player.body.world.colliders = ()
        player.camera.position = glm.vec3(0, 1.6, 20)
        system.update(0)
        sounds.play_discovery.assert_not_called()
        player.camera.position = glm.vec3(0, 1.6, 0)
        system.update(0)
        sounds.play_discovery.assert_called_once()

    def test_discovery_is_once_per_campaign_and_briefly_ducks_music(self):
        flags = set()
        system, _, sounds = self.system(flags)
        system.update(0)
        sounds.play_discovery.assert_called_once_with("blood_sting", 0.72 * settings.AMBIENCE_VOLUME)
        self.assertIn(StairBloodDiscovery.FLAG, flags)
        ducked = next(c.args[2] for c in sounds.loop.call_args_list if c.args[0] == MUSIC_CHANNEL)
        sounds.reset_mock()
        system.update(4)
        normal = next(c.args[2] for c in sounds.loop.call_args_list if c.args[0] == MUSIC_CHANNEL)
        self.assertAlmostEqual(ducked, normal * 0.3)
        sounds.play_discovery.assert_not_called()
        reloaded, _, reloaded_sounds = self.system(flags)
        reloaded.update(0)
        reloaded_sounds.play_discovery.assert_not_called()
        fresh, _, fresh_sounds = self.system()
        fresh.update(0)
        fresh_sounds.play_discovery.assert_called_once()

    def test_pause_creator_and_audio_toggle_do_not_consume_discovery(self):
        system, player, sounds = self.system()
        system.set_paused(True)
        system.update(1)
        system.set_paused(False)
        player.creator_mode = True
        system.update(1)
        player.creator_mode = False
        with patch.object(settings, "AUDIO_ENABLED", False):
            system.update(1)
        sounds.play_discovery.assert_not_called()
        self.assertNotIn(StairBloodDiscovery.FLAG, system._blood.flags)
        system.update(0)
        sounds.play_discovery.assert_called_once()

    def test_real_hospital_has_visible_blood_targets_only_after_transformation(self):
        campaign = Campaign()
        peaceful = campaign.load_level("peaceful")
        self.assertFalse(peaceful.level.stair_blood_targets)
        scene = campaign.load_level("start")
        self.assertEqual(len(scene.level.stair_blood_targets), 4)
        camera = Camera((-8, 1.6, 9), (-13, 0.02, 8), 60, 0.1, 100)
        self.assertTrue(StairBloodDiscovery(scene.level.stair_blood_targets, set()).visible(camera, scene.player.body.world))

    def test_reserved_discovery_channel_plays_even_with_busy_environment_channels(self):
        bank = HospitalSoundBank(load_audio_profile("abandoned")[0])
        channel = Mock()
        with patch.object(bank, "_ensure", return_value=True), patch.object(bank, "_sound", return_value="sample"), \
                patch("pygame.mixer.Channel", return_value=channel) as select:
            bank.play_discovery("blood_sting", 0.4)
        select.assert_called_once_with(DISCOVERY_CHANNEL)
        channel.play.assert_called_once_with("sample")
        self.assertLess(MUSIC_CHANNEL, FIRST_FOOTSTEP_CHANNEL)
        self.assertLess(DISCOVERY_CHANNEL, FIRST_FOOTSTEP_CHANNEL)

    def test_assets_have_verified_provenance_safe_levels_and_loop_seam(self):
        root = AUDIO_ROOT / "music"
        manifest = json.loads((root / "sources.json").read_text(encoding="utf-8"))
        self.assertEqual({s["license"] for s in manifest}, {"CC0-1.0", "CC-BY-3.0"})
        for item in manifest:
            path = root / item["file"]
            self.assertEqual(sha256(path.read_bytes()).hexdigest(), item["sha256"])
            with wave.open(str(path), "rb") as clip:
                self.assertEqual((clip.getnchannels(), clip.getsampwidth(), clip.getframerate()), (1, 2, 44100))
                pcm = array("h", clip.readframes(clip.getnframes()))
            self.assertAlmostEqual(len(pcm) / 44100, item["duration"])
            self.assertLessEqual(max(abs(v) for v in pcm), 20316)
            self.assertGreater(math.sqrt(sum(v * v for v in pcm) / len(pcm)), 200)
            if item["crossfade"]:
                jumps = sorted(abs(pcm[i + 1] - pcm[i]) for i in range(0, len(pcm) - 1, 20))
                self.assertLessEqual(abs(pcm[0] - pcm[-1]), max(5, jumps[int(len(jumps) * 0.99)] * 2))
            else:
                self.assertEqual(pcm[0], 0)
                self.assertEqual(pcm[-1], 0)


if __name__ == "__main__":
    unittest.main()
