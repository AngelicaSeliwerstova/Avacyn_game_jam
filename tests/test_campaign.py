from dataclasses import replace
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from config import controls, settings
from engine.core.application import Application
from engine.input.state import InputState
from engine.scene.transform import Transform
from game.campaign import Campaign
from game.entities.escape import EscapeGoal


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.model_patch = patch.object(settings, "PLAYER_MODEL", None)
        self.model_patch.start()
        self.addCleanup(self.model_patch.stop)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        base = {"floor_size": [20, 20], "spawn_position": [0, 1.6, 0],
                "spawn_target": [0, 1.6, -1], "objects": [
                    {"id": "exit", "type": "exit", "position": [3, 0, 0],
                     "required_keys": ["story_key"], "next_level": "second"}]}
        (root / "intro.json").write_text(json.dumps(base), encoding="utf-8")
        base["objects"][0].pop("next_level")
        base["objects"][0]["required_keys"] = []
        (root / "second.json").write_text(json.dumps(base), encoding="utf-8")
        levels_patch = patch("game.levels.LEVELS_ROOT", root)
        levels_patch.start()
        self.addCleanup(levels_patch.stop)


    def test_exit_requires_keys_and_requests_next_location_once(self):
        campaign = Campaign()
        scene = campaign.load_level("intro")
        goal = scene.session.goals[0]
        goal.transform = replace(goal.transform, position=tuple(scene.player.body.position))
        scene.session.update(0)
        self.assertIsNone(scene.session.next_level)
        for key in goal.required_keys:
            scene.player.inventory.add_key(key, key)
        scene.session.update(0)
        self.assertEqual(scene.session.next_level, "second")
        self.assertIsNone(scene.session.dialog)
        goal.transform = replace(goal.transform, position=(1000, 0, 1000))
        scene.session.update(0)
        self.assertEqual(scene.session.next_level, "second")

    def test_new_location_replaces_world_and_preserves_progress_and_inventory_binding(self):
        campaign = Campaign()
        old = campaign.load_level("intro")
        old.player.inventory.add_key("story_key", "Story key")
        old.player.flashlight.light.enabled = False
        campaign.progress.flags.add("intro_finished")
        scene = campaign.load_level("second")
        self.assertIsNot(old.level, scene.level)
        self.assertIsNot(old.player.body.world, scene.player.body.world)
        self.assertIsNot(old.session, scene.session)
        self.assertIs(scene.player.inventory, old.player.inventory)
        self.assertIs(scene.player._interactions.inventory, scene.player.inventory)
        self.assertTrue(scene.player.inventory.has_key("story_key"))
        self.assertFalse(scene.player.flashlight.light.enabled)
        self.assertEqual(campaign.progress.current_level, "second")
        self.assertEqual(campaign.progress.completed_levels, {"intro"})
        self.assertIn("intro_finished", campaign.progress.flags)
        spawn = scene.level.spawn_position
        self.assertAlmostEqual(scene.player.body.position.x, spawn[0])
        self.assertAlmostEqual(scene.player.body.position.y, spawn[1] - settings.PLAYER_EYE_HEIGHT)
        self.assertAlmostEqual(scene.player.body.position.z, spawn[2])
        scene.player.update(1 / 60, InputState())

    def test_final_exit_wins_and_restart_has_clean_campaign(self):
        campaign = Campaign()
        scene = campaign.load_level("second")
        scene.player.inventory.add_key("old", "Old key")
        goal = scene.session.goals[0]
        goal.transform = replace(goal.transform, position=tuple(scene.player.body.position))
        scene.session.update(0)
        self.assertIsNone(scene.session.next_level)
        self.assertEqual(scene.session.dialog.title, "Ты выбрался")
        fresh = Campaign()
        self.assertFalse(fresh.progress.inventory.has_key("old"))
        self.assertFalse(fresh.progress.completed_levels)

    def test_failed_load_does_not_advance_progress(self):
        campaign = Campaign()
        campaign.load_level("second")
        with self.assertRaises(ValueError):
            campaign.load_level("missing-location")
        self.assertEqual(campaign.progress.current_level, "second")
        self.assertFalse(campaign.progress.completed_levels)

    def test_exit_target_validation(self):
        for target in ("", " ", 42):
            with self.assertRaises(ValueError):
                EscapeGoal("exit", transform=Transform(), next_level=target)

    def test_application_replaces_all_scene_dependencies_without_recreating_window(self):
        campaign = Campaign()
        old = campaign.load_level("intro")
        scene = campaign.load_level("second")
        loader = Mock(return_value=scene)
        app = Application((640, 480), (320, 240), "test", 60, (0, 0, 0), (3, 3), False,
                          old.player, controls.INPUT_BINDINGS, old.level,
                          session=old.session, scene_loader=loader)
        old.session.next_level = "second"
        renderer, window, new_renderer = Mock(), Mock(), Mock()
        window.size = (640, 480)
        with patch.object(app, "_create_renderer", return_value=new_renderer):
            self.assertIs(app._change_level(renderer, window), new_renderer)
        renderer.release.assert_called_once_with(release_context=False)
        window.present.assert_called_once()
        loader.assert_called_once_with("second")
        self.assertIs(app._level, scene.level)
        self.assertIs(app._controlled_entity, scene.player)
        self.assertIs(app._session, scene.session)
        self.assertIs(app._systems, scene.systems)
        self.assertIs(app._snow, scene.snow)
        self.assertIs(app._debug_paths, scene.debug_paths)
        self.assertEqual(app._dynamic_lights, scene.player.dynamic_lights)


if __name__ == "__main__":
    unittest.main()
