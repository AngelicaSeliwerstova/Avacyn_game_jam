from dataclasses import dataclass

from engine.collision.aabb import AABB
from engine.scene.box import Box


@dataclass(frozen=True)
class Level:
    """Данные статичного уровня с объёмными блоками без привязки к GPU."""

    floor_size: tuple[float, float]
    floor_tile_size: float
    boxes: tuple[Box, ...]
    spawn_position: tuple[float, float, float]
    spawn_target: tuple[float, float, float]
    floor_colors: tuple[tuple[int, int, int], tuple[int, int, int]]

    def __post_init__(self):
        if any(length <= 0 for length in self.floor_size) or self.floor_tile_size <= 0:
            raise ValueError("Floor dimensions and tile size must be positive")
        if len(self.floor_colors) != 2 or any(
            len(color) != 3 or any(not 0 <= channel <= 255 for channel in color)
            for color in self.floor_colors
        ):
            raise ValueError("Floor needs two RGB colors with channels from 0 to 255")

    @property
    def floor_bounds(self) -> AABB:
        width, depth = self.floor_size
        return AABB(-width / 2, -depth / 2, width / 2, depth / 2)
