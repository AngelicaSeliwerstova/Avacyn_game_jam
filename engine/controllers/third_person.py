import math

import glm

from engine.collision.aabb import AABB
from engine.collision.aabb3d import AABB3D
from engine.collision.obb import OBB
from engine.raycasting.aabb import cast_ray


class ThirdPersonCamera:
    """Камера на отрезке от персонажа: быстро сжимается у стен и плавно возвращается."""

    def __init__(self, camera, colliders, objects=(), *, distance=3.2, height=0.65,
                 look_ahead=4.0, radius=0.18, recovery_speed=8.0, ground_height=0.0):
        if (any(not math.isfinite(v) or v <= 0 for v in (distance, look_ahead, radius, recovery_speed))
                or not math.isfinite(height) or height < 0 or not math.isfinite(ground_height)):
            raise ValueError("Third-person camera dimensions must be finite and positive; height may be zero")
        self.camera = camera
        self.distance, self.height = distance, height
        self.look_ahead, self.radius = look_ahead, radius
        self.recovery_speed, self.ground_height = recovery_speed, ground_height
        self._static = tuple(self._expand(collider) for collider in colliders)
        self._objects, self._states, self._dynamic = objects, None, ()
        self._length = None

    def _expand(self, collider):
        f, r = collider.footprint, self.radius
        footprint = (OBB(f.x, f.z, f.half_width + r, f.half_depth + r, f.yaw_degrees)
                     if isinstance(f, OBB) else AABB(f.min_x - r, f.min_z - r, f.max_x + r, f.max_z + r))
        return AABB3D(footprint, collider.bottom - r, collider.top + r)

    def update(self, delta_time, anchor, forward):
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Camera delta time must be finite and nonnegative")
        anchor, forward = glm.vec3(anchor), glm.normalize(glm.vec3(forward))
        states = tuple(obj.current_state for obj in self._objects)
        if states != self._states:
            self._dynamic = tuple(self._expand(box.collider) for state in states if state.collidable for box in state.boxes)
            self._states = states
        boom = -forward * self.distance + glm.vec3(0, self.height, 0)
        length = glm.length(boom)
        direction = boom / length
        hit = cast_ray(anchor, direction, self._static + self._dynamic, length)
        available = max(0.0, hit.distance - 0.03) if hit else length
        if direction.y < 0:
            floor_distance = (self.ground_height + self.radius - anchor.y) / direction.y
            available = min(available, max(0.0, floor_distance))
        if self._length is None or available < self._length:
            self._length = available
        else:
            self._length += (available - self._length) * (1 - math.exp(-self.recovery_speed * delta_time))
        self.camera.position = anchor + direction * self._length
        self.camera.target = anchor + forward * self.look_ahead

    @property
    def distance_from_player(self):
        return self._length or 0.0
