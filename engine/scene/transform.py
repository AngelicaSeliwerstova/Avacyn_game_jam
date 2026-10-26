from dataclasses import dataclass
import math

import glm


@dataclass(frozen=True)
class Transform:
    """Положение, поворот XYZ в градусах и масштаб объекта или его модели."""

    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)

    def __post_init__(self):
        if any(len(values) != 3 or not all(math.isfinite(v) for v in values)
               for values in (self.position, self.rotation, self.scale)):
            raise ValueError("Transform needs three finite coordinates per field")
        if any(value <= 0 for value in self.scale):
            raise ValueError("Transform scale must be positive")

    @property
    def matrix(self) -> glm.mat4:
        matrix = glm.translate(glm.mat4(1.0), glm.vec3(self.position))
        # Локальный поворот: сначала X, затем Y, затем Z.
        for angle, axis in reversed(tuple(zip(self.rotation, (
            glm.vec3(1, 0, 0), glm.vec3(0, 1, 0), glm.vec3(0, 0, 1),
        )))):
            matrix = glm.rotate(matrix, math.radians(angle), axis)
        return glm.scale(matrix, glm.vec3(self.scale))
