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

    def test_both_worlds_resolve_all_material_roles_to_existing_textures(self):
        materials = create_texture_settings()
        names = {material.name for material in materials.materials}
        for world in ("start", "peaceful"):
            level = create_level(world)
            used = {level.floor_material} | {box.material for box in
                    level.boxes + level.decorations + level.all_object_boxes if box.material is not None}
            self.assertTrue(used <= names, (world, used - names))
        for material in materials.materials:
            self.assertTrue(material.path.is_file(), material.path)

    def test_mattresses_use_textile_materials_without_color_overriding_texture(self):
        for world, finish in (("peaceful", "linen_ivory"), ("start", "linen_worn")):
            level = create_level(world)
            mattresses = [b for b in level.boxes if b.size in ((1.08, 0.15, 1.96), (1.14, 0.2, 2.05))]
            self.assertEqual(len(mattresses), 30)
            self.assertTrue(all(b.material == finish and b.color is None for b in mattresses))

    def test_department_floors_have_distinct_finishes_in_each_world(self):
        for world, lobby, surgery, ward in (
            ("peaceful", "terrazzo_gray", "tile_mint_clean", "linoleum_sage"),
            ("start", "floor_tile_dirty", "hospital_checker", "linoleum_green"),
        ):
            level = create_level(world)
            self.assertEqual(level.floor_material, lobby)
            for height, expected in ((4.8, surgery), (9.6, ward)):
                floors = [b for b in level.boxes if abs(b.collider.top - height) < 1e-5
                          and b.footprint.intersects_circle(24, 18, 0.01)]
                self.assertTrue(floors)
                self.assertTrue(all(b.material == expected for b in floors))

    def test_both_texture_resolutions_have_complete_catalogs(self):
        fixed_small = {"brick", "plaster", "hospital_tiles", "hospital_floor"}
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
