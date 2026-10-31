import json
from pathlib import Path

from config import settings
from engine.scene.box import Box
from engine.scene.level import Level
from engine.scene.lighting import LightFlicker, Lighting, PointLight
from engine.scene.interaction import Interaction
from game.levels.cameras import load_fixed_cameras
from game.levels.creator import load_creator_objects
from game.levels.objects import build_objects


def _box(data) -> Box:
    data = dict(data)
    for field in ("position", "size", "emission", "color"):
        if data.get(field) is not None:
            data[field] = tuple(data[field])
    if data.get("interaction") is not None:
        data["interaction"] = Interaction(**data["interaction"])
    return Box(**data)


def _light(data) -> PointLight:
    data = dict(data)
    data["position"] = tuple(data["position"])
    if "color" in data:
        data["color"] = tuple(data["color"])
    if data.get("flicker") is not None:
        data["flicker"] = LightFlicker(**data["flicker"])
    return PointLight(**data)


def load_location(path: Path) -> Level:
    """Собирает самостоятельную локацию и её данные Creator."""
    data = json.loads(path.read_text(encoding="utf-8"))
    cameras_path = path.with_name(f"{path.stem}_cameras.json")
    objects_path = path.with_name(f"{path.stem}_objects.json")
    lights_path = path.with_name(f"{path.stem}_lights.json")
    cameras = load_fixed_cameras(cameras_path)
    creator_objects = load_creator_objects(objects_path)
    lighting = data.get("lighting", {})
    level = Level(
        floor_size=tuple(data["floor_size"]),
        floor_tile_size=data.get("floor_tile_size", settings.FLOOR_TILE_SIZE),
        floor_colors=tuple(tuple(color) for color in data.get("floor_colors", settings.FLOOR_COLORS)),
        floor_material=data.get("floor_material", "concrete"),
        base_height=data.get("base_height", 0.0),
        floor_heights=tuple(data.get("floor_heights", (data.get("base_height", 0.0),))),
        floor_labels=tuple(data.get("floor_labels", ())),
        floor_hints=tuple(data.get("floor_hints", ())),
        boxes=tuple(_box(box) for box in data.get("boxes", ())),
        spawn_position=tuple(data["spawn_position"]),
        spawn_target=tuple(data["spawn_target"]),
        snow_enabled=data.get("snow_enabled", False),
        lighting=Lighting(
            tuple(lighting.get("ambient", (0.3, 0.3, 0.3))),
            tuple(_light(light) for light in lighting.get("lights", ())),
            lighting.get("shadow_resolution", 128),
        ),
        objects=build_objects(data.get("objects", ())),
        decorations=creator_objects,
        creator_objects=creator_objects,
        creator_objects_path=objects_path,
        creator_lights_path=lights_path,
        creator_room_height=data.get("room_height", 3.3),
        fixed_cameras=cameras or (),
        authored_fixed_cameras=cameras or (),
        fixed_cameras_authored=cameras is not None,
        camera_save_path=cameras_path,
        visual_style=data.get("visual_style", "default"),
    )
    if data.get("layout") in ("hospital", "hospital_first_floor", "hospital_peaceful"):
        from game.levels.hospital import build_hospital
        level = build_hospital(level, peaceful=data.get("layout") == "hospital_peaceful")
    elif data.get("layout") is not None:
        raise ValueError(f"Unknown location layout: {data['layout']!r}")
    return level
