from dataclasses import dataclass
import math

from engine.collision.aabb import AABB
from engine.scene.box import Box
from engine.scene.lighting import Lighting
from engine.scene.object import SceneObject


@dataclass(frozen=True)
class Level:
    """Статичная геометрия и объекты с состояниями без привязки к GPU."""

    floor_size: tuple[float, float]
    floor_tile_size: float
    boxes: tuple[Box, ...]
    spawn_position: tuple[float, float, float]
    spawn_target: tuple[float, float, float]
    floor_colors: tuple[tuple[int, int, int], tuple[int, int, int]]
    floor_material: str | None = None
    floor_heights: tuple[float, ...] = (0.0,)
    goal_position: tuple[float, float, float] | None = None
    goal_radius: float = 1.0
    snow_enabled: bool = True
    lighting: Lighting | None = None
    decorations: tuple[Box, ...] = ()
    base_height: float = 0.0
    floor_labels: tuple[str, ...] = ()
    floor_hints: tuple[str, ...] = ()
    objects: tuple[SceneObject, ...] = ()

    def __post_init__(self):
        if len({obj.name for obj in self.objects}) != len(self.objects):
            raise ValueError("Scene object names must be unique within a level")
        if not math.isfinite(self.base_height):
            raise ValueError("Level base height must be finite")
        if not self.floor_heights or any(not math.isfinite(y) for y in self.floor_heights):
            raise ValueError("Level floor heights must be finite and nonempty")
        if any(items and len(items) != len(self.floor_heights) for items in (self.floor_labels, self.floor_hints)):
            raise ValueError("Floor labels and hints must match floor heights")
        if any(length <= 0 for length in self.floor_size) or self.floor_tile_size <= 0:
            raise ValueError("Floor dimensions and tile size must be positive")
        light_count = len(self.lighting.lights) if self.lighting is not None else 0
        if any(box.emission_light is not None and box.emission_light >= light_count
               for box in self.boxes + self.decorations + self.all_object_boxes):
            raise ValueError("Emissive panel must reference a light in this level")
        if len(self.floor_colors) != 2 or any(
            len(color) != 3 or any(not 0 <= channel <= 255 for channel in color)
            for color in self.floor_colors
        ):
            raise ValueError("Floor needs two RGB colors with channels from 0 to 255")

    @property
    def object_boxes(self) -> tuple[Box, ...]:
        return tuple(box for obj in self.objects for box in obj.boxes)

    @property
    def static_shadow_boxes(self) -> tuple[Box, ...]:
        return tuple(box for obj in self.objects if obj.static_shadows for box in obj.boxes)

    @property
    def all_object_boxes(self) -> tuple[Box, ...]:
        """Все состояния нужны для проверки материалов и построения сетки света."""
        return tuple(box for obj in self.objects for state in obj.states.values() for box in state.boxes)

    @property
    def floor_bounds(self) -> AABB:
        width, depth = self.floor_size
        return AABB(-width / 2, -depth / 2, width / 2, depth / 2)
