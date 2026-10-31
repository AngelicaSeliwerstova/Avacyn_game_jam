from pathlib import Path
from dataclasses import replace

from config import settings
from engine.scene.level import Level
from engine.scene.box import Box
from engine.scene.object import ObjectState, SceneObject
from engine.scene.transform import Transform
from engine.scene.tiled_level import load_tiled_level
from game.entities.escape import EscapeGoal


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
    # Временная вторая локация: выход в дальнем конце коридора.
    goal = EscapeGoal("corridor_escape", transform=Transform(position=(6, 0, -6)), radius=1.2)
    marker = Box((6, 0.02, -6), (1.8, 0.04, 1.8), material="rust")
    return replace(
        level, boxes=boxes, floor_material=settings.CORRIDOR_FLOOR_MATERIAL,
        goal_position=goal.transform.position, goal_radius=goal.radius,
        decorations=level.decorations + (marker,),
        objects=level.objects + (SceneObject(goal.name, {"default": ObjectState()}, entity=goal),),
        snow_enabled=False,
    )
