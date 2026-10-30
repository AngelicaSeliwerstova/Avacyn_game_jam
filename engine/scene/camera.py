from dataclasses import dataclass
import math

import glm


@dataclass(frozen=True)
class FixedCameraZone:
    """Статичный ракурс, активный пока игрок находится внутри заданной области."""

    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]
    position: tuple[float, float, float]
    target: tuple[float, float, float]

    def __post_init__(self):
        points = (self.minimum, self.maximum, self.position, self.target)
        if any(len(point) != 3 or not all(math.isfinite(value) for value in point) for point in points):
            raise ValueError("Fixed camera points must contain three finite coordinates")
        if any(low >= high for low, high in zip(self.minimum, self.maximum)):
            raise ValueError("Fixed camera zone dimensions must be positive")
        if self.position == self.target:
            raise ValueError("Fixed camera position and target must differ")

    def contains(self, point: tuple[float, float, float]) -> bool:
        return all(low <= value <= high for value, low, high in zip(point, self.minimum, self.maximum))


class Camera:
    """Перспективная камера: откуда смотрим и как проецируем мир на экран."""

    def __init__(
        self,
        position: tuple[float, float, float],
        target: tuple[float, float, float],
        fov_degrees: float,
        near: float,
        far: float,
    ):
        if not 0 < fov_degrees < 180:
            raise ValueError("Camera FOV must be between 0 and 180 degrees")
        if not 0 < near < far:
            raise ValueError("Camera clipping planes must satisfy 0 < near < far")

        self.position = glm.vec3(position)
        self.target = glm.vec3(target)
        self.up = glm.vec3(0.0, 1.0, 0.0)
        self.fov_degrees = fov_degrees
        self.near = near
        self.far = far

    @property
    def view_matrix(self) -> glm.mat4:
        direction = self.target - self.position
        if glm.length(glm.cross(direction, self.up)) < 1e-6:
            raise ValueError("Camera direction must be nonzero and not parallel to up")
        return glm.lookAt(self.position, self.target, self.up)

    def projection_matrix(self, aspect_ratio: float) -> glm.mat4:
        if aspect_ratio <= 0:
            raise ValueError("Camera aspect ratio must be positive")
        return glm.perspective(
            glm.radians(self.fov_degrees), aspect_ratio, self.near, self.far
        )
