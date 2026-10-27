from dataclasses import dataclass, field
import math


@dataclass(frozen=True)
class OBB:
    """Поворачиваемый прямоугольник XZ для вертикальных блоков."""

    x: float
    z: float
    half_width: float
    half_depth: float
    yaw_degrees: float
    _cos: float = field(init=False, repr=False, compare=False)
    _sin: float = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if (not all(math.isfinite(v) for v in (self.x, self.z, self.half_width, self.half_depth, self.yaw_degrees))
                or min(self.half_width, self.half_depth) <= 0):
            raise ValueError("OBB needs finite coordinates and positive dimensions")
        angle = math.radians(self.yaw_degrees)
        object.__setattr__(self, "_cos", math.cos(angle))
        object.__setattr__(self, "_sin", math.sin(angle))

    def local_point(self, x, z):
        return self.local_direction(x - self.x, z - self.z)

    def local_direction(self, x, z):
        return self._cos * x - self._sin * z, self._sin * x + self._cos * z

    @property
    def extent_x(self):
        return abs(self._cos) * self.half_width + abs(self._sin) * self.half_depth

    @property
    def extent_z(self):
        return abs(self._sin) * self.half_width + abs(self._cos) * self.half_depth

    @property
    def min_x(self):
        return self.x - self.extent_x

    @property
    def max_x(self):
        return self.x + self.extent_x

    @property
    def min_z(self):
        return self.z - self.extent_z

    @property
    def max_z(self):
        return self.z + self.extent_z

    def intersects_circle(self, x: float, z: float, radius: float) -> bool:
        x, z = self.local_point(x, z)
        dx, dz = max(abs(x) - self.half_width, 0), max(abs(z) - self.half_depth, 0)
        return dx * dx + dz * dz < radius * radius

    def axis_interval(self, other: float, radius: float, axis: int):
        """Точный отрезок контакта круга вдоль мировой оси, включая скруглённые углы."""
        origin = self.local_point(0, other) if axis == 0 else self.local_point(other, 0)
        direction = self.local_direction(1, 0) if axis == 0 else self.local_direction(0, 1)
        intervals = []
        # Расширенный на круг прямоугольник: две полосы и четыре круга в углах.
        for hx, hz in ((self.half_width + radius, self.half_depth),
                       (self.half_width, self.half_depth + radius)):
            entry, exit = -math.inf, math.inf
            for start, delta, half in zip(origin, direction, (hx, hz)):
                if abs(delta) < 1e-12:
                    if abs(start) >= half:
                        break
                else:
                    a, b = (-half - start) / delta, (half - start) / delta
                    entry, exit = max(entry, min(a, b)), min(exit, max(a, b))
                    if entry > exit:
                        break
            else:
                intervals.append((entry, exit))
        for x in (-self.half_width, self.half_width):
            for z in (-self.half_depth, self.half_depth):
                dx, dz = origin[0] - x, origin[1] - z
                center = -(dx * direction[0] + dz * direction[1])
                perpendicular = dx * direction[1] - dz * direction[0]
                discriminant = radius * radius - perpendicular * perpendicular
                if discriminant > 0:
                    reach = math.sqrt(discriminant)
                    intervals.append((center - reach, center + reach))
        if not intervals:
            return None
        return min(a for a, _ in intervals), max(b for _, b in intervals)
