import math
from collections.abc import Iterable

import glm

from engine.collision.aabb import AABB


class CollisionWorld:
    """Перемещает круг игрока между неподвижными прямоугольниками."""

    # Допуск для координат, округлённых до float32 при передаче в glm.vec3.
    _CONTACT_EPSILON = 1e-6

    def __init__(self, colliders: Iterable[AABB], bounds: AABB | None = None):
        self.colliders = tuple(colliders)
        self.bounds = bounds

    def is_blocked(self, position: glm.vec3, radius: float) -> bool:
        x, z = position.x, position.z
        if self.bounds is not None:
            bounds = self.bounds
            if (
                x - radius < bounds.min_x or x + radius > bounds.max_x
                or z - radius < bounds.min_z or z + radius > bounds.max_z
            ):
                return True
        return any(box.intersects_circle(x, z, radius) for box in self.colliders)

    def move(
        self,
        position: glm.vec3,
        displacement: glm.vec3,
        radius: float,
        max_step: float,
    ) -> glm.vec3:
        if radius <= 0 or max_step <= 0:
            raise ValueError("Player radius and collision step must be positive")
        if self.bounds is not None and (
            self.bounds.max_x - self.bounds.min_x < radius * 2
            or self.bounds.max_z - self.bounds.min_z < radius * 2
        ):
            raise ValueError("Player does not fit inside collision world bounds")

        distance = math.hypot(displacement.x, displacement.z)
        if distance == 0:
            return glm.vec3(position)

        # Подшаги делают скольжение вокруг углов плавнее.
        step_length = min(max_step, radius * 0.5)
        steps = math.ceil(distance / step_length)
        dx, dz = displacement.x / steps, displacement.z / steps
        x, z = float(position.x), float(position.z)
        for _ in range(steps):
            x = self._move_axis(x, z, dx, radius, axis=0)
            z = self._move_axis(z, x, dz, radius, axis=1)
        return glm.vec3(x, position.y, z)

    def _move_axis(
        self, origin: float, other: float, delta: float, radius: float, axis: int,
    ) -> float:
        if delta == 0:
            return origin
        destination = origin + delta
        if self.bounds is not None:
            low = self.bounds.min_x if axis == 0 else self.bounds.min_z
            high = self.bounds.max_x if axis == 0 else self.bounds.max_z
            destination = max(low + radius, min(high - radius, destination))

        for box in self.colliders:
            low = box.min_x if axis == 0 else box.min_z
            high = box.max_x if axis == 0 else box.max_z
            other_low = box.min_z if axis == 0 else box.min_x
            other_high = box.max_z if axis == 0 else box.max_x
            gap = max(other_low - other, 0.0, other - other_high)
            if gap >= radius:
                continue

            # Сечение препятствия, расширенного на круг игрока. Проверяем
            # весь путь по оси: даже тонкая стена не пропускается между кадрами.
            reach = math.sqrt(max(0.0, radius * radius - gap * gap))
            entry, exit = low - reach, high + reach
            if delta > 0 and origin <= entry + self._CONTACT_EPSILON:
                destination = min(destination, entry)
            elif delta < 0 and origin >= exit - self._CONTACT_EPSILON:
                destination = max(destination, exit)
        return destination
