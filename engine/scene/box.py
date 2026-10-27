from dataclasses import dataclass, replace
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

    def __post_init__(self):
        validate_rgb(self.emission)
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
        translation = glm.rotate(translation, glm.radians(self.yaw_degrees), glm.vec3(0, 1, 0))
        # Исходный CubeMesh имеет сторону 2.
        return glm.scale(translation, glm.vec3(self.size) * 0.5)

    @property
    def footprint(self) -> AABB | OBB:
        x, _, z = self.position
        width, _, depth = self.size
        if self.yaw_degrees % 360 != 0:
            return OBB(x, z, width / 2, depth / 2, self.yaw_degrees)
        return AABB(x - width / 2, z - depth / 2, x + width / 2, z + depth / 2)

    @property
    def bounds_half_size(self) -> tuple[float, float, float]:
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

    @property
    def collider(self) -> AABB3D:
        return AABB3D(self.footprint, self.position[1] - self.size[1] / 2,
                      self.position[1] + self.size[1] / 2)
