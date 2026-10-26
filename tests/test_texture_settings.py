from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pygame

from config import settings
from game.levels import create_level
from game.materials import create_texture_settings


class TextureSettingsTests(unittest.TestCase):
    def test_texture_paths_do_not_depend_on_working_directory(self):
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                materials = create_texture_settings()
            finally:
                os.chdir(original)
        root = Path(__file__).resolve().parents[1] / "resources" / "textures"
        self.assertEqual(materials.floor, root / settings.FLOOR_TEXTURE.format(size=settings.TEXTURE_RESOLUTION))
        self.assertEqual(materials.wall, root / settings.WALL_TEXTURE.format(size=settings.TEXTURE_RESOLUTION))
        self.assertTrue(materials.floor.is_file())
        self.assertTrue(materials.wall.is_file())

    def test_textures_can_be_disabled_together_or_individually(self):
        with patch.object(settings, "TEXTURES_ENABLED", False):
            self.assertIsNone(create_texture_settings())
        with patch.object(settings, "FLOOR_TEXTURE", None):
            materials = create_texture_settings()
            self.assertIsNone(materials.floor)
            self.assertIsNotNone(materials.wall)
        with patch.object(settings, "WALL_TEXTURE", None):
            materials = create_texture_settings()
            self.assertIsNotNone(materials.floor)
            self.assertIsNone(materials.wall)

    def test_invalid_repeat_sizes_and_filtering_are_rejected(self):
        materials = create_texture_settings()
        for changes in ({"floor_world_size": 0}, {"wall_world_size": float("nan")},
                        {"anisotropy": 0}, {"anisotropy": float("inf")}):
            with self.assertRaises(ValueError):
                replace(materials, **changes)

    def test_all_material_kinds_are_used_by_existing_scenes(self):
        materials = create_texture_settings()
        names = {material.name for material in materials.materials}
        used = set()
        for name in ("stairs", "corridor", "demo"):
            level = create_level(name)
            used.add(level.floor_material)
            used.update(box.material for box in level.boxes)
        self.assertEqual(used, names)
        for material in materials.materials:
            self.assertTrue(material.path.is_file(), material.path)

    def test_both_texture_resolutions_have_complete_catalogs(self):
        fixed_small = {"brick", "plaster", "hospital_tiles"}
        for size in (128, 256):
            with patch.object(settings, "TEXTURE_RESOLUTION", size):
                materials = create_texture_settings()
            for material in materials.materials:
                expected = 128 if material.name in fixed_small else size
                image = pygame.image.load(str(material.path))
                self.assertEqual(image.get_size(), (expected, expected), material.path)

    def test_unsupported_resolution_is_rejected(self):
        with patch.object(settings, "TEXTURE_RESOLUTION", 512):
            with self.assertRaises(ValueError):
                create_texture_settings()


if __name__ == "__main__":
    unittest.main()
