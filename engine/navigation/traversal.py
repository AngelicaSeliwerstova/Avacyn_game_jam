from dataclasses import dataclass
import math

from engine.collision.obb import OBB


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
        self._static = tuple(colliders)
        self._states = None
        self._dynamic = ()
        self._static_cache = {}
        self._revision = 0

    @property
    def revision(self):
        states = tuple(obj.current_state for obj in self._objects)
        if states != self._states:
            self._states = states
            self._dynamic = tuple(box.collider for state in states if state.collidable for box in state.boxes)
            self._revision += 1
        return self._revision

    @staticmethod
    def _hits_rectangle(a, b, min_x, max_x, min_z, max_z):
        entry, exit = 0.0, 1.0
        for start, end, low, high in ((a[0], b[0], min_x, max_x),
                                      (a[1], b[1], min_z, max_z)):
            delta = end - start
            if abs(delta) < 1e-12:
                if start < low or start > high:
                    return False
            else:
                t1, t2 = (low - start) / delta, (high - start) / delta
                entry, exit = max(entry, min(t1, t2)), min(exit, max(t1, t2))
                if entry > exit:
                    return False
        return True

    def _hits_footprint(self, a, b, footprint):
        if isinstance(footprint, OBB):
            a, b = footprint.local_point(*a), footprint.local_point(*b)
            min_x, max_x = -footprint.half_width, footprint.half_width
            min_z, max_z = -footprint.half_depth, footprint.half_depth
        else:
            min_x, max_x = footprint.min_x, footprint.max_x
            min_z, max_z = footprint.min_z, footprint.max_z
        # A swept circular body makes two strips and four rounded corners.
        # A single expanded rectangle traps valid positions near door corners.
        radius = max(0.0, self.radius - 1e-6)
        if (self._hits_rectangle(a, b, min_x - radius, max_x + radius, min_z, max_z)
                or self._hits_rectangle(a, b, min_x, max_x, min_z - radius, max_z + radius)):
            return True
        dx, dz = b[0] - a[0], b[1] - a[1]
        length_squared = dx * dx + dz * dz
        for x in (min_x, max_x):
            for z in (min_z, max_z):
                t = (max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / length_squared))
                     if length_squared > 1e-12 else 0.0)
                if (a[0] + t * dx - x) ** 2 + (a[1] + t * dz - z) ** 2 < radius * radius:
                    return True
        return False

    def _clear(self, a, b, colliders):
        low, high = min(a[1], b[1]), max(a[1], b[1]) + self.height
        for collider in colliders:
            f = collider.footprint
            if (collider.top <= low + self.step_height + 1e-5 or collider.bottom >= high - 1e-5
                    or f.min_x - self.radius > max(a[0], b[0]) or f.max_x + self.radius < min(a[0], b[0])
                    or f.min_z - self.radius > max(a[2], b[2]) or f.max_z + self.radius < min(a[2], b[2])):
                continue
            entry, exit = 0.0, 1.0
            dy = b[1] - a[1]
            if abs(dy) > 1e-12:
                t1 = (collider.bottom - self.height + 1e-5 - a[1]) / dy
                t2 = (collider.top - 1e-5 - a[1]) / dy
                entry, exit = max(entry, min(t1, t2)), min(exit, max(t1, t2))
                if entry > exit:
                    continue
            start = (a[0] + entry * (b[0] - a[0]), a[2] + entry * (b[2] - a[2]))
            end = (a[0] + exit * (b[0] - a[0]), a[2] + exit * (b[2] - a[2]))
            if self._hits_footprint(start, end, f):
                return False
        return True

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
