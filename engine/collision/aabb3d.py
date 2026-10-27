from dataclasses import dataclass
from math import isfinite

from engine.collision.aabb import AABB
from engine.collision.obb import OBB


@dataclass(frozen=True)
class AABB3D:
    """Объём препятствия, включая нижнюю и верхнюю границы."""

    footprint: AABB | OBB
    bottom: float
    top: float

    def __post_init__(self):
        if not all(isfinite(y) for y in (self.bottom, self.top)) or self.bottom >= self.top:
            raise ValueError("Collider bottom must be finite and lower than its top")
