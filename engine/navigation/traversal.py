from dataclasses import dataclass
import math

from engine.collision.aabb import AABB
from engine.collision.aabb3d import AABB3D
from engine.collision.obb import OBB
from engine.raycasting.aabb import cast_ray


@dataclass(frozen=True)
class TraversalProfile:
    radius: float
    height: float
    step_height: float

    def __post_init__(self):
        if (not all(math.isfinite(v) and v > 0 for v in (self.radius, self.height, self.step_height))
                or self.step_height >= self.height):
            raise ValueError("Traversal profile needs positive dimensions and a step lower than its height")


class NavigationTraversal:
    """Запоминает неподвижные препятствия; двери проверяет по текущей позе."""

    def __init__(self, colliders, objects, bounds, profile: TraversalProfile):
        self.radius, self.height, self.step_height = profile.radius, profile.height, profile.step_height
        self._bounds, self._objects = bounds, objects
        self._static = tuple(self._expand(collider) for collider in colliders)
        self._states = None
        self._dynamic = ()
        self._static_cache = {}
        self._revision = 0

    @property
    def revision(self):
        states = tuple(obj.current_state for obj in self._objects)
        if states != self._states:
            self._states = states
            self._dynamic = tuple(self._expand(box.collider) for state in states if state.collidable for box in state.boxes)
            self._revision += 1
        return self._revision

    def _expand(self, collider):
        f = collider.footprint
        if isinstance(f, OBB):
            footprint = OBB(f.x, f.z, f.half_width + self.radius, f.half_depth + self.radius, f.yaw_degrees)
        else:
            footprint = AABB(f.min_x - self.radius, f.min_z - self.radius,
                             f.max_x + self.radius, f.max_z + self.radius)
        # Верхняя отметка исходного блока нужна для пропуска пола и ступеней.
        expanded = AABB3D(footprint, collider.bottom - self.height / 2 + 1e-5,
                          collider.top + self.height / 2 - 1e-5)
        return collider.bottom, collider.top, expanded

    def _clear(self, a, b, colliders):
        low, high = min(a[1], b[1]), max(a[1], b[1]) + self.height
        candidates = (c for bottom, top, c in colliders
                      if top > low + self.step_height + 1e-5 and bottom < high - 1e-5
                      and c.footprint.min_x <= max(a[0], b[0]) and c.footprint.max_x >= min(a[0], b[0])
                      and c.footprint.min_z <= max(a[2], b[2]) and c.footprint.max_z >= min(a[2], b[2]))
        origin = (a[0], a[1] + self.height / 2, a[2])
        delta = tuple(y - x for x, y in zip(a, b))
        distance = math.hypot(*delta)
        return cast_ray(origin, delta if distance > 1e-8 else (0, 1, 0), candidates, distance) is None

    def can_walk(self, a, b, terrain=False, *, cache=True):
        a, b = tuple(a), tuple(b)
        for p in (a, b):
            if self._bounds is not None and (p[0] - self.radius < self._bounds.min_x
                    or p[0] + self.radius > self._bounds.max_x or p[2] - self.radius < self._bounds.min_z
                    or p[2] + self.radius > self._bounds.max_z):
                return False
        key = (min(a, b), max(a, b))
        if not terrain:
            if not cache:
                if not self._clear(a, b, self._static):
                    return False
            elif key not in self._static_cache:
                self._static_cache[key] = self._clear(a, b, self._static)
            if cache and not self._static_cache[key]:
                return False
        self.revision
        return self._clear(a, b, self._dynamic)
