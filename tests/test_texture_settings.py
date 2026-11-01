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
            self.assertEqual(len(mattresses), 29)
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
                shape = (expected * 4, expected) if material.name.startswith("sign_patient_") else (expected, expected)
                if material.name.startswith("story_"):
                    shape = ((192, 192) if material.name == "story_clock" else
                             (256, 192) if material.name == "story_drawing" else (256, 144))
                self.assertEqual(image.get_size(), shape, material.path)

    def test_third_floor_signs_cover_every_room_and_resolve_to_readable_materials(self):
        from game.levels.room_signs import PATIENT_SIGNS
        level = create_level("start")
        signs = [b for b in level.decorations if b.material and b.material.startswith("sign_patient_")]
        self.assertEqual(len(signs), 15)
        self.assertEqual({b.material for b in signs}, {f"sign_{name}" for name in PATIENT_SIGNS})
        self.assertTrue(all(b.position[1] > 9.6 and b.local_texture and b.color is None for b in signs))
        names = {b.interaction.name for b in signs}
        self.assertTrue({f"Палата {number}" for number in range(301, 314)} <= names)
        self.assertIn("Пост медсестры", names)

    def test_unsupported_resolution_is_rejected(self):
        with patch.object(settings, "TEXTURE_RESOLUTION", 512):
            with self.assertRaises(ValueError):
                create_texture_settings()

    def test_ward_303_entire_plaque_is_visible_from_reported_corridor_position(self):
        import math
        from engine.raycasting.aabb import cast_ray
        level = create_level("start")
        sign = next(b for b in level.decorations if b.material == "sign_patient_room_2")
        origin = (-14.87, 11.53, -3.66)
        colliders = tuple(b.collider for b in level.collision_boxes)
        # Both ends and both vertical corners must clear the nurse-office wall.
        for dx in (-sign.size[0] / 2, sign.size[0] / 2):
            for dy in (-sign.size[1] / 2, sign.size[1] / 2):
                point = (sign.position[0] + dx, sign.position[1] + dy, sign.position[2] + 0.02)
                direction = tuple(v - o for v, o in zip(point, origin))
                self.assertIsNone(cast_ray(origin, direction, colliders, math.dist(origin, point)))


if __name__ == "__main__":
    unittest.main()
