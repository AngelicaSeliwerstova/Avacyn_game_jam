import json
from pathlib import Path

from engine.scene.box import Box


def creator_objects_path() -> Path:
    return Path(__file__).resolve().parents[2] / "resources" / "levels" / "maze_objects.json"


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
            }
            for box in objects
        ],
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
