from dataclasses import dataclass

from engine.collision.aabb import AABB
from engine.scene.box import Box


@dataclass(frozen=True)
class Level:
    """Данные статичного одноэтажного уровня без привязки к GPU."""

    floor_size: tuple[float, float]
    floor_tile_size: float
    boxes: tuple[Box, ...]
    spawn_position: tuple[float, float, float]
    spawn_target: tuple[float, float, float]

    def __post_init__(self):
        if any(length <= 0 for length in self.floor_size) or self.floor_tile_size <= 0:
            raise ValueError("Floor dimensions and tile size must be positive")

    @property
    def floor_bounds(self) -> AABB:
        width, depth = self.floor_size
        return AABB(-width / 2, -depth / 2, width / 2, depth / 2)
