import json
from pathlib import Path

from engine.scene.box import Box


def load_creator_objects(path: Path) -> tuple[Box, ...]:
    if not path.exists():
        return ()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("objects"), list):
        raise ValueError(f"Creator object layout must contain an 'objects' list: {path}")
    result = []
    for index, value in enumerate(data["objects"]):
        if not isinstance(value, dict):
            raise ValueError(f"Object {index + 1} must be an object: {path}")
        try:
            result.append(Box(
                position=tuple(value["position"]),
                size=tuple(value["size"]),
                material=value["material"],
                yaw_degrees=value.get("yaw_degrees", 0.0),
                orientation=tuple(value.get("orientation", (1, 0, 0, 0))),
                creator_group=value.get("creator_group"),
                creator_pivot=tuple(value["creator_pivot"]) if value.get("creator_pivot") else None,
                emission=tuple(value.get("emission", (0, 0, 0))),
                color=tuple(value["color"]) if value.get("color") is not None else None,
                local_texture=value.get("local_texture", False),
            ))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid object {index + 1} in {path}: {error}") from error
    return tuple(result)


def save_creator_objects(path: Path, objects: tuple[Box, ...]) -> None:
    data = {
        "objects": [
            {
                "position": box.position,
                "size": box.size,
                "material": box.material,
                "yaw_degrees": box.yaw_degrees,
                "orientation": box.orientation,
                "creator_group": box.creator_group,
                "creator_pivot": box.creator_pivot,
                "emission": box.emission,
                "color": box.color,
                "local_texture": box.local_texture,
            }
            for box in objects
        ],
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_removed_objects(path):
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    groups = data.get("removed_groups") if isinstance(data, dict) else None
    if not isinstance(groups, list) or any(not isinstance(group, str) or not group for group in groups):
        raise ValueError(f"Invalid removed object groups: {path}")
    return set(groups)


def save_removed_objects(path, groups):
    path.write_text(json.dumps({"removed_groups": sorted(groups)}, indent=2) + "\n", encoding="utf-8")
