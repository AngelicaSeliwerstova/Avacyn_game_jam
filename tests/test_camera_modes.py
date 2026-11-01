"""Camera selection changes real movement/view and survives story location changes."""
import unittest
from unittest.mock import patch

import glm

from config import settings
from engine.input.state import InputState
from game.campaign import Campaign
from test_tank_controls import make_player


class CameraModeTests(unittest.TestCase):
    def test_third_person_uses_mouse_and_strafing_then_restores_fixed_cameras(self):
        player = make_player()
        player.update(0, InputState())
        self.assertTrue(player.fixed_camera_effect_active)
        player.set_camera_mode('third_person')
        self.assertFalse(player.fixed_camera_effect_active)
        self.assertIsNone(player._active_fixed_camera())
        start = glm.vec3(player.body.position)
        yaw = player.controller.yaw_degrees
        player.update(.1, InputState(right=1))
        self.assertGreater(glm.distance(start, player.body.position), .1)
        self.assertAlmostEqual(player.controller.yaw_degrees, yaw)
        player.update(.1, InputState(mouse_delta=(20, 10)))
        self.assertNotEqual(player.controller.yaw_degrees, yaw)
        self.assertGreater(glm.distance(player.camera.position, player.body.position), .5)
        player.set_camera_mode('cameras')
        self.assertTrue(player.fixed_camera_effect_active)
        start = glm.vec3(player.body.position)
        player.update(.1, InputState(right=1))
        self.assertLess(glm.distance(start, player.body.position), 1e-6)

    @patch.object(settings, 'AUDIO_ENABLED', False)
    def test_campaign_preserves_mode_and_story_camera_in_both_modes(self):
        campaign = Campaign(camera_mode='third_person')
        first = campaign.load_level('peaceful')
        self.addCleanup(first.session.release)
        scene = campaign.load_level('start')
        self.addCleanup(scene.session.release)
        self.assertEqual(scene.player.camera_mode, 'third_person')
        scene.player.update(0, InputState())
        self.assertFalse(scene.player.fixed_camera_effect_active)
        campaign.set_camera_mode('cameras')
        self.assertTrue(scene.player.fixed_camera_effect_active)
        scene.player.story_camera = ((-13.2, 6.65, -17.8), (-16, 5.6, -20.5))
        campaign.set_camera_mode('third_person')
        self.assertLess(glm.distance(scene.player.camera.position, glm.vec3(-13.2, 6.65, -17.8)), 1e-5)
        self.assertFalse(scene.player.fixed_camera_effect_active)
