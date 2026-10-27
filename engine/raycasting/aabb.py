from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import math

from engine.collision.aabb3d import AABB3D


@dataclass(frozen=True)
class RayHit:
    index: int
    distance: float
    position: tuple[float, float, float]


def cast_ray(origin: Sequence[float], direction: Sequence[float],
             colliders: Iterable[AABB3D], max_distance: float) -> RayHit | None:
    """Ближайшее пересечение луча с AABB; расстояние измеряется в мировых единицах."""
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
        lower = (box.footprint.min_x, box.bottom, box.footprint.min_z)
        upper = (box.footprint.max_x, box.top, box.footprint.max_z)
        entry, exit = 0.0, nearest
        for start, delta, low, high in zip(origin, direction, lower, upper):
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
