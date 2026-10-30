import json
import math
from pathlib import Path

from engine.scene.box import Box
from engine.scene.camera import FixedCameraZone
from engine.collision.obb import OBB
from config import settings


def camera_layout_path() -> Path:
    level_name = Path(settings.MAZE_LAYOUT).stem
    return Path(__file__).resolve().parents[2] / "resources" / "levels" / f"{level_name}_cameras.json"


def load_fixed_cameras(path: Path) -> tuple[FixedCameraZone, ...] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cameras"), list):
        raise ValueError(f"Camera layout must contain a 'cameras' list: {path}")
    cameras = []
    for index, value in enumerate(data["cameras"]):
        if not isinstance(value, dict):
            raise ValueError(f"Camera {index + 1} must be an object: {path}")
        try:
            points = {}
            for name in ("minimum", "maximum", "position", "target"):
                point = value[name]
                if not isinstance(point, (list, tuple)) or len(point) != 3:
                    raise ValueError(f"{name} must contain three coordinates")
                points[name] = tuple(point)
            cameras.append(FixedCameraZone(**points))
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid camera {index + 1} in {path}: {error}") from error
    return tuple(cameras)


def save_fixed_cameras(path: Path, cameras: tuple[FixedCameraZone, ...]) -> None:
    data = {
        "cameras": [
            {
                "minimum": camera.minimum,
                "maximum": camera.maximum,
                "position": camera.position,
                "target": camera.target,
            }
            for camera in cameras
        ],
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def camera_model_boxes(camera: FixedCameraZone, led_on: bool) -> tuple[Box, ...]:
    direction_x = camera.target[0] - camera.position[0]
    direction_z = camera.target[2] - camera.position[2]
    yaw = math.degrees(math.atan2(-direction_x, -direction_z))
    angle = math.radians(yaw)
    cosine, sine = math.cos(angle), math.sin(angle)
    origin_x, origin_y, origin_z = camera.position

    def at(local_position):
        x, y, z = local_position
        return origin_x + cosine * x + sine * z, origin_y + y, origin_z - sine * x + cosine * z

    def part(local_position, size, color, emission=(0.0, 0.0, 0.0)):
        return Box(
            at(local_position), size, yaw_degrees=yaw, color=color, emission=emission,
        )

    return (
        part((0.0, 0.0, 0.13), (0.34, 0.28, 0.05), (0.24, 0.27, 0.28)),
        part((0.0, 0.0, 0.055), (0.13, 0.13, 0.16), (0.18, 0.2, 0.21)),
        part((0.0, 0.0, -0.105), (0.4, 0.29, 0.34), (0.22, 0.25, 0.26),
             emission=(0.025, 0.03, 0.032)),
        part((0.0, 0.154, -0.105), (0.2, 0.018, 0.22), (0.34, 0.37, 0.38)),
        part((0.0, -0.154, -0.105), (0.2, 0.018, 0.22), (0.09, 0.11, 0.12)),
        part((0.0, 0.0, -0.29), (0.27, 0.22, 0.04), (0.09, 0.11, 0.12)),
        part((0.0, 0.0, -0.326), (0.17, 0.17, 0.06), (0.36, 0.39, 0.4)),
        part((0.0, 0.0, -0.36), (0.125, 0.125, 0.014), (0.025, 0.09, 0.14),
             emission=(0.025, 0.08, 0.13)),
        part((-0.025, 0.027, -0.369), (0.018, 0.018, 0.006), (0.55, 0.76, 0.86),
             emission=(0.18, 0.3, 0.36)),
        part((0.15, 0.145, -0.12), (0.024, 0.014, 0.024), (0.35, 0.025, 0.018),
             emission=(1.2, 0.025, 0.012) if led_on else (0.09, 0.008, 0.004)),
        part((-0.215, 0.0, -0.12), (0.025, 0.18, 0.22), (0.12, 0.14, 0.15)),
        part((0.215, 0.0, -0.12), (0.025, 0.18, 0.22), (0.12, 0.14, 0.15)),
        part((0.0, 0.0, -0.21), (0.24, 0.018, 0.018), (0.38, 0.41, 0.42)),
    )


def camera_wall_normal(position: tuple[float, float, float], collider) -> tuple[float, float, float] | None:
    if collider.top - collider.bottom < 2.0:
        return None
    footprint = collider.footprint
    if isinstance(footprint, OBB):
        local_x, local_z = footprint.local_point(position[0], position[2])
        distance_x = abs(abs(local_x) - footprint.half_width)
        distance_z = abs(abs(local_z) - footprint.half_depth)
        if distance_x <= distance_z:
            local_normal = (1.0 if local_x >= 0 else -1.0, 0.0)
        else:
            local_normal = (0.0, 1.0 if local_z >= 0 else -1.0)
        angle = math.radians(footprint.yaw_degrees)
        normal = (
            math.cos(angle) * local_normal[0] + math.sin(angle) * local_normal[1],
            -math.sin(angle) * local_normal[0] + math.cos(angle) * local_normal[1],
        )
        return normal[0], 0.0, normal[1]

    distances = (
        (abs(position[0] - footprint.min_x), (-1.0, 0.0, 0.0)),
        (abs(position[0] - footprint.max_x), (1.0, 0.0, 0.0)),
        (abs(position[2] - footprint.min_z), (0.0, 0.0, -1.0)),
        (abs(position[2] - footprint.max_z), (0.0, 0.0, 1.0)),
    )
    return min(distances, key=lambda item: item[0])[1]
