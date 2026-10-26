from dataclasses import dataclass

import glm

from engine.collision.aabb import AABB
from engine.collision.aabb3d import AABB3D


@dataclass(frozen=True)
class Box:
    """Общий источник размеров и положения для модели и коллайдера."""

    position: tuple[float, float, float]
    size: tuple[float, float, float]

    def __post_init__(self):
        if any(length <= 0 for length in self.size):
            raise ValueError("Box dimensions must be positive")

    @property
    def model_matrix(self) -> glm.mat4:
        translation = glm.translate(glm.mat4(1.0), glm.vec3(self.position))
        # Исходный CubeMesh имеет сторону 2.
        return glm.scale(translation, glm.vec3(self.size) * 0.5)

    @property
    def footprint(self) -> AABB:
        x, _, z = self.position
        width, _, depth = self.size
        return AABB(x - width / 2, z - depth / 2, x + width / 2, z + depth / 2)

    @property
    def collider(self) -> AABB3D:
        return AABB3D(self.footprint, self.position[1] - self.size[1] / 2,
                      self.position[1] + self.size[1] / 2)
