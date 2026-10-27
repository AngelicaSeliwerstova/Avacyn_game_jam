from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import math

from engine.collision.aabb3d import AABB3D
from engine.collision.obb import OBB


@dataclass(frozen=True)
class RayHit:
    index: int
    distance: float
    position: tuple[float, float, float]


def cast_ray(origin: Sequence[float], direction: Sequence[float],
             colliders: Iterable[AABB3D], max_distance: float) -> RayHit | None:
    """Пересечение луча с обычными и повёрнутыми вертикальными блоками."""
    origin, direction = tuple(origin), tuple(direction)
    if (len(origin) != 3 or len(direction) != 3
            or not all(math.isfinite(v) for v in origin + direction)
            or not math.isfinite(max_distance) or max_distance < 0):
        raise ValueError("Ray needs finite 3D coordinates and a nonnegative finite range")
    length = math.hypot(*direction)
    if length == 0:
        raise ValueError("Ray direction must be nonzero")
    direction = tuple(v / length for v in direction)
    nearest, result = max_distance, None
    for index, box in enumerate(colliders):
        start_point, ray_direction = origin, direction
        footprint = box.footprint
        if isinstance(footprint, OBB):
            x, z = footprint.local_point(origin[0], origin[2])
            dx, dz = footprint.local_direction(direction[0], direction[2])
            start_point, ray_direction = (x, origin[1], z), (dx, direction[1], dz)
            lower = (-footprint.half_width, box.bottom, -footprint.half_depth)
            upper = (footprint.half_width, box.top, footprint.half_depth)
        else:
            lower = (footprint.min_x, box.bottom, footprint.min_z)
            upper = (footprint.max_x, box.top, footprint.max_z)
        entry, exit = 0.0, nearest
        for start, delta, low, high in zip(start_point, ray_direction, lower, upper):
            if delta == 0:
                if start < low or start > high:
                    break
            else:
                a, b = (low - start) / delta, (high - start) / delta
                entry, exit = max(entry, min(a, b)), min(exit, max(a, b))
                if entry > exit:
                    break
        else:
            if result is None or entry < nearest:
                nearest = entry
                point = tuple(p + d * entry for p, d in zip(origin, direction))
                result = RayHit(index, entry, point)
    return result
