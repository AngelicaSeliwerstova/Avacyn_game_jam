from pathlib import Path
from dataclasses import replace

from config import settings
from engine.scene.level import Level
from engine.scene.tiled_level import load_tiled_level


def create_corridor_level() -> Level:
    map_path = Path(__file__).resolve().parents[2] / "resources" / "levels" / "corridor.tmx"
    level = load_tiled_level(
        map_path, eye_height=settings.PLAYER_EYE_HEIGHT, floor_colors=settings.FLOOR_COLORS,
    )
    materials = settings.CORRIDOR_WALL_MATERIALS
    if not materials:
        raise ValueError("Corridor needs at least one wall material")
    depth = level.floor_size[1]

    def material_for_z(z: float) -> str:
        section = int((depth / 2 - z) / depth * len(materials))
        return materials[max(0, min(len(materials) - 1, section))]

    boxes = tuple(replace(box, material=material_for_z(box.position[2])) for box in level.boxes)
    return replace(level, boxes=boxes, floor_material=settings.CORRIDOR_FLOOR_MATERIAL)
