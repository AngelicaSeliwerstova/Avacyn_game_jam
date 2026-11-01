import itertools
import math
from pathlib import Path
import tempfile
import unittest

import glm

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.input.state import InputState
from engine.scene.box import Box
from engine.scene.level import Level
from game.entities.player import create_player
from game.levels.creator import load_creator_objects, save_creator_objects
from game.levels.creator_presets import creator_presets, place_preset, rotate_group, remove_group


class CreatorPresetTests(unittest.TestCase):
    def test_catalog_has_furniture_equipment_and_both_world_palettes(self):
        ruined, peaceful = creator_presets(), creator_presets(True)
        self.assertGreaterEqual(len(ruined), 30)
        self.assertEqual([p.name for p in ruined], [p.name for p in peaceful])
        self.assertEqual(len({p.name for p in ruined}), len(ruined))
        for presets in (ruined, peaceful):
            for preset in presets:
                placed = place_preset(preset, (3, 4.8, 2))
                self.assertTrue(placed)
                self.assertEqual(len({b.creator_group for b in placed}), 1)
                self.assertAlmostEqual(min(b.collider.bottom for b in placed), 4.8, places=5)
        self.assertNotEqual(ruined[1].boxes[0].material, peaceful[1].boxes[0].material)

    def test_rotation_preserves_assembly_and_bounds_enclose_rendered_corners(self):
        sofa = place_preset(creator_presets()[1], (2, 0, 3))
        other = place_preset(creator_presets()[1], (9, 0, 3))
        objects = sofa + other
        for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            objects = rotate_group(objects, 1, axis, 35)
        self.assertEqual(objects[len(sofa):], other)
        for a, b in itertools.combinations(range(len(sofa)), 2):
            self.assertAlmostEqual(math.dist(sofa[a].position, sofa[b].position),
                                   math.dist(objects[a].position, objects[b].position), places=5)
        for box in objects[:len(sofa)]:
            corners = [box.model_matrix * glm.vec4(*c, 1) for c in itertools.product((-1, 1), repeat=3)]
            bounds = box.bounds_half_size
            for i in range(3):
                self.assertAlmostEqual(min(c[i] for c in corners), box.position[i] - bounds[i], places=5)
                self.assertAlmostEqual(max(c[i] for c in corners), box.position[i] + bounds[i], places=5)
            self.assertAlmostEqual(box.collider.bottom, min(c.y for c in corners), places=5)
        self.assertEqual(remove_group(objects, 2), other)

    def test_full_geometry_and_groups_survive_save_reload_and_legacy_files(self):
        objects = rotate_group(place_preset(creator_presets()[1], (0, 9.6, 0)), 0, (1, 0, 0), 90)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "objects.json"
            save_creator_objects(path, objects)
            self.assertEqual(load_creator_objects(path), objects)
            self.assertEqual(remove_group(load_creator_objects(path), 1), ())
            path.write_text('{"objects":[{"position":[0,1,0],"size":[1,2,1],"material":"rust"}]}')
            self.assertEqual(load_creator_objects(path), (Box((0, 1, 0), (1, 2, 1), material="rust"),))

    def test_creator_input_places_rotates_moves_and_deletes_complete_sofa(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "objects.json"
            level = Level((30, 30), 1, (), (0, settings.PLAYER_EYE_HEIGHT, 0), (0, settings.PLAYER_EYE_HEIGHT, -1), ((80, 80, 80),) * 2,
                          creator_objects_path=path)
            world = CollisionWorld3D((), level.floor_bounds)
            player = create_player(level, world, creator_mode=True)
            player.camera.position = glm.vec3(0, 5, 0)
            player._creator_pitch = -math.pi / 2 + 0.01
            player.update(0, InputState(next_creator_preset=True, add_object=True))
            placed = player.creator_object_boxes
            self.assertGreater(len(placed), 1)
            player.camera.position = glm.vec3(0, 5, 0)
            player.update(0, InputState(creator_axis_z=True, rotate_creator_object=True))
            rotated = player.creator_object_boxes
            self.assertNotEqual(rotated, placed)
            self.assertEqual(load_creator_objects(path), rotated)
            player.camera.position = glm.vec3(5, 5, 0)
            player.update(0, InputState(move_creator_object=True))
            moved = player.creator_object_boxes
            self.assertEqual(len(moved), len(placed))
            self.assertGreater(moved[0].position[0] - rotated[0].position[0], 3)
            player.update(0, InputState(delete_camera=True))
            self.assertEqual(player.creator_object_boxes, ())
            self.assertEqual(load_creator_objects(path), ())
