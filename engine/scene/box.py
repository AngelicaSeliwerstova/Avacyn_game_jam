from dataclasses import dataclass, replace
from functools import cached_property
import math

import glm

from engine.collision.aabb import AABB
from engine.collision.aabb3d import AABB3D
from engine.collision.obb import OBB
from engine.scene.lighting import validate_rgb
from engine.scene.interaction import Interaction


@dataclass(frozen=True)
class Box:
    """Общий источник размеров и положения для модели и коллайдера."""

    position: tuple[float, float, float]
    size: tuple[float, float, float]
    material: str | None = None
    emission: tuple[float, float, float] = (0.0, 0.0, 0.0)
    interaction: Interaction | None = None
    emission_light: int | None = None
    yaw_degrees: float = 0.0
    local_texture: bool = False
    decal: bool = False
    color: tuple[float, float, float] | None = None

    orientation: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)
    authored_group: str | None = None
    creator_group: str | None = None
    creator_pivot: tuple[float, float, float] | None = None

    def __post_init__(self):
        if self.creator_group is not None and (not isinstance(self.creator_group, str) or not self.creator_group):
            raise ValueError("Creator group must be a nonempty string")
        if self.creator_pivot is not None and (
            len(self.creator_pivot) != 3 or not all(math.isfinite(v) for v in self.creator_pivot)
        ):
            raise ValueError("Creator pivot must contain three finite coordinates")
        if (len(self.orientation) != 4 or not all(math.isfinite(v) for v in self.orientation)
                or abs(sum(v * v for v in self.orientation) - 1) > 1e-5):
            raise ValueError("Box orientation must be a unit quaternion")
        validate_rgb(self.emission)
        if self.color is not None and (
            len(self.color) != 3 or any(not math.isfinite(channel) or not 0 <= channel <= 1
                                        for channel in self.color)
        ):
            raise ValueError("Box color channels must be finite values from 0 to 1")
        if not math.isfinite(self.yaw_degrees):
            raise ValueError("Box yaw must be finite")
        if any(length <= 0 for length in self.size):
            raise ValueError("Box dimensions must be positive")
        if self.material is not None and not self.material:
            raise ValueError("Material name must not be empty")
        if self.emission_light is not None and (not isinstance(self.emission_light, int) or self.emission_light < 0):
            raise ValueError("Emissive light index must be a nonnegative integer")

    @property
    def model_matrix(self) -> glm.mat4:
        translation = glm.translate(glm.mat4(1.0), glm.vec3(self.position))
        if self.orientation != (1.0, 0.0, 0.0, 0.0):
            translation *= glm.mat4_cast(glm.quat(*self.orientation))
        translation = glm.rotate(translation, glm.radians(self.yaw_degrees), glm.vec3(0, 1, 0))
        # Исходный CubeMesh имеет сторону 2.
        return glm.scale(translation, glm.vec3(self.size) * 0.5)

    @cached_property
    def footprint(self) -> AABB | OBB:
        x, _, z = self.position
        if self.orientation != (1.0, 0.0, 0.0, 0.0):
            hx, _, hz = self.bounds_half_size
            return AABB(x - hx, z - hz, x + hx, z + hz)
        width, _, depth = self.size
        if self.yaw_degrees % 360 != 0:
            return OBB(x, z, width / 2, depth / 2, self.yaw_degrees)
        return AABB(x - width / 2, z - depth / 2, x + width / 2, z + depth / 2)

    @cached_property
    def bounds_half_size(self) -> tuple[float, float, float]:
        if self.orientation != (1.0, 0.0, 0.0, 0.0):
            matrix = self.model_matrix
            return tuple(sum(abs(matrix[column][row]) for column in range(3)) for row in range(3))
        angle = math.radians(self.yaw_degrees)
        c, s = abs(math.cos(angle)), abs(math.sin(angle))
        x, y, z = (v / 2 for v in self.size)
        return c * x + s * z, y, s * x + c * z

    def rotated_around(self, pivot, angle_degrees):
        x, y, z = (v - p for v, p in zip(self.position, pivot))
        angle = math.radians(angle_degrees)
        c, s = math.cos(angle), math.sin(angle)
        return replace(self, position=(pivot[0] + c * x + s * z, pivot[1] + y,
                                       pivot[2] - s * x + c * z),
                       yaw_degrees=self.yaw_degrees + angle_degrees)

    @cached_property
    def collider(self) -> AABB3D:
        return AABB3D(self.footprint, self.position[1] - self.bounds_half_size[1],
                      self.position[1] + self.bounds_half_size[1])
