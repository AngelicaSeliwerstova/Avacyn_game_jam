import math
from collections.abc import Iterable

import glm

from engine.collision.aabb import AABB
from engine.collision.obb import OBB
from engine.collision.sweep import circle_contact


class CollisionWorld:
    """Перемещает круг игрока между неподвижными прямоугольниками."""

    # Допуск для координат, округлённых до float32 при передаче в glm.vec3.
    _CONTACT_EPSILON = 1e-6

    def __init__(self, colliders: Iterable[AABB | OBB], bounds: AABB | None = None):
        self.colliders = tuple(colliders)
        self.bounds = bounds
        self._rotated = any(isinstance(box, OBB) for box in self.colliders)

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
            if self._rotated:
                x, z = self._slide(x, z, dx, dz, radius)
            else:
                x = self._move_axis(x, z, dx, radius, axis=0)
                z = self._move_axis(z, x, dz, radius, axis=1)
        return glm.vec3(x, position.y, z)

    def _slide(self, x, z, dx, dz, radius):
        for _ in range(5):
            length = math.hypot(dx, dz)
            if length < 1e-10:
                break
            hit = None
            for box in self.colliders:
                contact = circle_contact(box, x, z, dx, dz, radius)
                if contact is not None and (hit is None or contact[0] < hit[0]):
                    hit = contact
            if self.bounds is not None:
                b = self.bounds
                for start, movement, low, high, nx, nz in (
                        (x, dx, b.min_x + radius, b.max_x - radius, 1, 0),
                        (z, dz, b.min_z + radius, b.max_z - radius, 0, 1)):
                    if abs(movement) < 1e-12:
                        continue
                    t = ((low if movement < 0 else high) - start) / movement
                    sign = 1 if movement < 0 else -1
                    if 0 <= t <= 1 and (hit is None or t < hit[0]):
                        hit = t, nx * sign, nz * sign
            if hit is None:
                x, z = x + dx, z + dz
                break
            t, nx, nz = hit
            # Leave a tiny gap so conversion back to float32 cannot put the body
            # inside the rail. Preserve only the motion tangent to the contact.
            travel = max(0, t - 1e-6 / length)
            x, z = x + dx * travel, z + dz * travel
            dx, dz = dx * (1 - t), dz * (1 - t)
            inward = min(0, dx * nx + dz * nz)
            dx, dz = dx - inward * nx, dz - inward * nz
        return x, z

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
            if isinstance(box, OBB):
                interval = box.axis_interval(other, radius, axis)
                if interval is None:
                    continue
                entry, exit = interval
                if delta > 0 and origin <= entry + self._CONTACT_EPSILON:
                    destination = min(destination, entry)
                elif delta < 0 and origin >= exit - self._CONTACT_EPSILON:
                    destination = max(destination, exit)
                continue
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
