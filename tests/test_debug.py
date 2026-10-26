import unittest
from unittest.mock import Mock, patch

import pygame

from config import controls
from engine.collision.world3d import CollisionWorld3D
from engine.core.application import Application
from engine.debug.panel import DebugSettings, DeveloperPanel
from engine.debug.profiler import FrameProfiler
from engine.input.state import InputState
from engine.scene.box import Box
from engine.scene.level import Level
from game.entities.player import create_player
from game.entities.player_state import MovementState


class DebugTests(unittest.TestCase):
    def test_fps_is_frames_over_elapsed_time_including_frame_pacing(self):
        profiler = FrameProfiler(0.04)
        self.assertFalse(profiler.record(0.01, 0.002, 0.004))
        self.assertTrue(profiler.record(0.03, 0.004, 0.008))
        self.assertAlmostEqual(profiler.metrics.fps, 50)
        self.assertAlmostEqual(profiler.metrics.frame_ms, 20)
        self.assertAlmostEqual(profiler.metrics.update_ms, 3)
        self.assertAlmostEqual(profiler.metrics.render_ms, 6)
        self.assertFalse(profiler.record(0, 0, 0))

    def test_panel_throttles_details_and_resets_samples_on_toggle(self):
        panel = DeveloperPanel(DebugSettings(refresh_interval=0.04))
        details = Mock(return_value=("POSITION",))
        panel.update(0.01, 0, 0, details)
        details.assert_not_called()
        self.assertEqual(panel.text, "")
        panel.toggle()
        panel.update(0.01, 0, 0, details)
        initial = panel.text
        panel.update(0.01, 0, 0, details)
        self.assertEqual(panel.text, initial)
        self.assertEqual(details.call_count, 1)
        panel.update(0.02, 0, 0, details)
        self.assertIn("FPS: 75.0", panel.text)
        panel.toggle()
        panel.toggle()
        panel.update(0.01, 0, 0, details)
        self.assertIn("FPS: ...", panel.text)

    def test_f3_toggles_without_repeats_or_releasing_mouse(self):
        app = Application((640, 480), (320, 240), "test", 60, (0, 0, 0), (3, 3), False,
                          Mock(), controls.INPUT_BINDINGS, Mock())
        device, window = Mock(), Mock()
        key = controls.INPUT_BINDINGS.toggle_debug
        events = [pygame.event.Event(pygame.KEYDOWN, key=key),
                  pygame.event.Event(pygame.KEYDOWN, key=key, repeat=True)]
        with patch("pygame.event.get", return_value=events):
            app._handle_events(device, window)
        self.assertTrue(app._debug.enabled)
        device.release.assert_not_called()
        with patch("pygame.event.get", return_value=events[:1]):
            app._handle_events(device, window)
        self.assertFalse(app._debug.enabled)

    def test_player_status_tracks_real_motion_and_not_held_buttons(self):
        level = Level((10, 10), 1, (Box((0, 1.5, -2), (4, 3, 1)),),
                      (0, 1.6, 2), (0, 1.6, 1), ((80, 80, 80),) * 2)
        world = CollisionWorld3D((b.collider for b in level.boxes), level.floor_bounds)
        player = create_player(level, world)
        self.assertEqual(player.movement_state, MovementState.IDLE)
        player.update(1 / 60, InputState(forward=1))
        self.assertEqual(player.movement_state, MovementState.WALKING)
        player.update(1 / 60, InputState(forward=1, sprint=True))
        self.assertEqual(player.movement_state, MovementState.RUNNING)
        player.update(1 / 60, InputState(jump=True))
        self.assertEqual(player.movement_state, MovementState.RISING)
        states = set()
        for _ in range(120):
            player.update(1 / 60, InputState())
            states.add(player.movement_state)
            self.assertEqual(player.transform.position, tuple(player.body.position))
        self.assertIn(MovementState.FALLING, states)
        self.assertEqual(player.movement_state, MovementState.IDLE)
        for _ in range(120):
            player.update(1 / 60, InputState(forward=1, sprint=True))
        self.assertEqual(player.movement_state, MovementState.IDLE)
        self.assertAlmostEqual(player.body.horizontal_speed, 0)
        self.assertIn("MOVE: IDLE", "\n".join(player.debug_lines))
