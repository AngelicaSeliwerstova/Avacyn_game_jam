from dataclasses import dataclass


@dataclass(frozen=True)
class AABB:
    """Прямоугольник в плоскости XZ для столкновений на одном этаже."""

    min_x: float
    min_z: float
    max_x: float
    max_z: float

    def __post_init__(self):
        if not self.min_x < self.max_x or not self.min_z < self.max_z:
            raise ValueError("Collider bounds must have positive width and depth")

    def intersects_circle(self, x: float, z: float, radius: float) -> bool:
        closest_x = max(self.min_x, min(self.max_x, x))
        closest_z = max(self.min_z, min(self.max_z, z))
        return (x - closest_x) ** 2 + (z - closest_z) ** 2 < radius ** 2
