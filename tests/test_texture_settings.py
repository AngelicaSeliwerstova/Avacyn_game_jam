from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from config import settings
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
        self.assertEqual(materials.floor, root / settings.FLOOR_TEXTURE)
        self.assertEqual(materials.wall, root / settings.WALL_TEXTURE)
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


if __name__ == "__main__":
    unittest.main()
