from pathlib import Path
import tempfile
import unittest

import glm

from engine.collision.world3d import CollisionWorld3D
from engine.rendering.renderer import Renderer
from game.entities.player import create_player
from game.companions import CompanionSystem
from game.levels import create_level
from game.levels.location import load_location
from game.levels.creator import load_removed_objects, save_removed_objects


class AuthoredRemovalTests(unittest.TestCase):
    def test_original_sofa_deletion_removes_all_parts_collision_and_survives_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "start.json"
            path.write_text(Path("resources/levels/start.json").read_text(encoding="utf-8"), encoding="utf-8")
            level = load_location(path)
            world = CollisionWorld3D((b.collider for b in level.collision_boxes), level.floor_bounds,
                                     objects=level.objects)
            player = create_player(level, world, creator_mode=True)
            companions = CompanionSystem(level, player)
            sofa = next(b for b in level.boxes if b.authored_group and
                        b.authored_group.startswith("floor_1/sofa:") and b.size[1] == 0.35)
            group = sofa.authored_group
            parts = tuple(b for b in level.boxes + level.decorations if b.authored_group == group)
            self.assertGreater(len(parts), 5)
            x, _, z = sofa.position
            feet = glm.vec3(x, 0, z)
            self.assertTrue(world.is_blocked(feet, 0.1, 1.8))
            player.camera.position = glm.vec3(x, 2.5, z)
            player.camera.target = glm.vec3(x, 0, z)
            player._delete_nearest_editor_item()
            self.assertEqual(level.removed_object_groups, {group})
            self.assertEqual(load_removed_objects(level.removed_objects_path), {group})
            self.assertFalse(world.is_blocked(feet, 0.1, 1.8))
            companions.update(0)
            for ally in companions.companions:
                self.assertFalse(ally.body.world.is_blocked(feet, 0.1, 1.8))
            loaded = load_location(path)
            self.assertEqual(loaded.removed_object_groups, {group})
            self.assertFalse(any(b.authored_group == group for b in loaded.collision_boxes))
            peaceful_path = Path(directory) / "peaceful.json"
            peaceful_path.write_text(Path("resources/levels/peaceful.json").read_text(encoding="utf-8"), encoding="utf-8")
            self.assertEqual(load_location(peaceful_path).removed_object_groups, set())

            renderer = Renderer.__new__(Renderer)
            renderer._base_level = loaded
            renderer._static_objects = renderer._prepare_objects(loaded.boxes + loaded.decorations)
            renderer._object_boxes = ()
            renderer._creator_objects = renderer._creator_light_objects = renderer._camera_marker_objects = ()
            renderer._rebuild_objects()
            self.assertFalse(any(item[0].authored_group == group for item in renderer._objects))

    def test_authored_objects_are_not_deleted_through_walls(self):
        level = create_level("start")
        world = CollisionWorld3D((b.collider for b in level.collision_boxes), level.floor_bounds, objects=level.objects)
        player = create_player(level, world, creator_mode=True)
        # Look at the south-wall sofas from outside the building.
        player.camera.position = glm.vec3(-16.8, 1, 17)
        player.camera.target = glm.vec3(-16.8, 1, 10)
        player._delete_nearest_editor_item()
        self.assertFalse(level.removed_object_groups)

    def test_bed_groups_are_complete_stable_and_separate_on_each_floor(self):
        first, second = create_level("start"), create_level("start")
        groups = lambda level: tuple(b.authored_group for b in level.boxes + level.decorations)
        self.assertEqual(groups(first), groups(second))
        for height in (4.8, 9.6):
            bed = next(b for b in first.boxes if b.size == (1.18, 0.2, 2.15)
                       and height < b.position[1] < height + 1)
            parts = [b for b in first.boxes + first.decorations if b.authored_group == bed.authored_group]
            self.assertGreater(len(parts), 8)
            self.assertTrue(all(height <= b.position[1] < height + 2 for b in parts))

    def test_removed_file_is_optional_and_invalid_data_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "map_removed.json"
            self.assertEqual(load_removed_objects(path), set())
            save_removed_objects(path, {"b", "a"})
            self.assertEqual(load_removed_objects(path), {"a", "b"})
            path.write_text('{"removed_groups":[12]}')
            with self.assertRaises(ValueError):
                load_removed_objects(path)
