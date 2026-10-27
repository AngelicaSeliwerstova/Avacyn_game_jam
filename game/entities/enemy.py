from dataclasses import dataclass, replace
from enum import Enum
import math

import glm

from config import settings
from engine.navigation.traversal import NavigationTraversal, TraversalProfile
from engine.physics.character import CharacterBody
from engine.scene.box import Box
from engine.scene.entity import Entity
from engine.scene.object import ObjectState, SceneObject
from engine.scene.transform import Transform


class EnemyState(Enum):
    CHASE = "CHASE"
    WAITING = "WAITING"


@dataclass(frozen=True)
class EnemySettings:
    speed: float = settings.ENEMY_SPEED
    repath_interval: float = settings.ENEMY_REPATH_INTERVAL
    stop_distance: float = settings.ENEMY_STOP_DISTANCE
    radius: float = settings.ENEMY_RADIUS
    height: float = settings.ENEMY_HEIGHT
    step_height: float = settings.ENEMY_STEP_HEIGHT

    def __post_init__(self):
        if any(not math.isfinite(v) or v <= 0 for v in vars(self).values()) or self.step_height >= self.height:
            raise ValueError("Enemy settings must be positive and finite; step_height must be lower than height")


class Enemy(Entity):
    """Улитка всегда знает позицию игрока, но доходит до неё только физическим путём."""

    def __init__(self, name: str, position, tuning: EnemySettings | None = None):
        position = self._point(position)
        super().__init__(name=name, transform=Transform(position=position))
        self.tuning = tuning or EnemySettings()
        self.body: CharacterBody | None = None
        self.state = EnemyState.CHASE
        self._yaw = 0.0
        self._path = []
        self.path_complete = False
        self._path_timer = self._blocked_time = 0.0
        self._planned_goal = None
        self._planned_revision = -1
        self._parts = self._make_parts()
        self.scene_object = SceneObject(name, {"default": ObjectState(self._geometry())},
                                        entity=self, static_shadows=False)

    @staticmethod
    def _point(point):
        if len(point) != 3 or not all(math.isfinite(v) for v in point):
            raise ValueError("Enemy positions need three finite world coordinates")
        return tuple(point)

    @property
    def path_length(self):
        return len(self._path)

    @property
    def remaining_path(self):
        return tuple(self._path)

    def bind(self, world, level):
        self.body = CharacterBody(
            self.transform.position, world, radius=self.tuning.radius, height=self.tuning.height,
            step_height=self.tuning.step_height, gravity=settings.GRAVITY,
            collision_max_step=settings.COLLISION_MAX_STEP, physics_step=settings.PHYSICS_STEP,
            camera_smoothing=settings.STAIR_CAMERA_SMOOTHING, jump_height=0,
        )
        self._graph = level.navigation
        self._navigation = NavigationTraversal(
            (box.collider for box in level.boxes),
            tuple(obj for obj in level.objects if not isinstance(obj.entity, Enemy)), level.floor_bounds,
            TraversalProfile(self.tuning.radius, self.tuning.height, self.tuning.step_height),
        )

    def update(self, delta_time, target_position):
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Enemy delta time must be finite and nonnegative")
        if self.body is None:
            raise RuntimeError("Enemy must be bound to a collision world before updating")
        target = self._point(target_position)
        position = tuple(self.body.position)
        self._path_timer -= delta_time
        moved = self._planned_goal is None or math.dist(target, self._planned_goal) > 0.5
        changed = self._navigation.revision != self._planned_revision
        arrived_far = not self._path and self.path_complete and math.dist(position, target) > self.tuning.stop_distance
        if self._path_timer <= 0 and (moved or changed or arrived_far or self._blocked_time > 0.4):
            self._replan(position, target)

        advanced = False
        while self._path and self._near(position, self._path[0], 0.14):
            self._path.pop(0)
            advanced = True
        if advanced:
            self._smooth(position)
        velocity = glm.vec3(0)
        self.state = EnemyState.WAITING
        if self._path:
            goal = self._path[0]
            final = self.path_complete and len(self._path) == 1
            if final and abs(position[1] - target[1]) < 0.01 and self._navigation.can_walk(position, target, cache=False):
                goal = target
            delta = glm.vec3(goal) - self.body.position
            delta.y = 0
            distance = glm.length(delta)
            stopping = self.tuning.stop_distance if final else 0.08
            if distance > stopping and delta_time > 0:
                self._yaw = math.degrees(math.atan2(-delta.x, -delta.z))
                velocity = delta / distance * min(self.tuning.speed, (distance - stopping) / delta_time)
            self.state = EnemyState.CHASE
        self.body.update(delta_time, velocity)
        if glm.length(velocity) > 0.01 and self.body.horizontal_speed < 0.02:
            self._blocked_time += delta_time
        else:
            self._blocked_time = 0.0
        pose = Transform(position=tuple(self.body.position), rotation=(0, self._yaw, 0))
        if pose != self.transform:
            self.transform = pose
            self.scene_object.set_geometry(self._geometry())

    def _near(self, a, b, distance):
        return math.hypot(a[0] - b[0], a[2] - b[2]) <= distance and abs(a[1] - b[1]) <= self.tuning.step_height + 0.01

    def _replan(self, position, target):
        if self._graph is not None:
            path = self._graph.find_path(position, target, self._navigation)
            self._path, self.path_complete = list(path.points), path.complete
        else:
            clear = abs(position[1] - target[1]) < 0.01 and self._navigation.can_walk(position, target, cache=False)
            self._path, self.path_complete = ([target] if clear else []), clear
        self._path_timer = self.tuning.repath_interval
        self._planned_goal, self._planned_revision = target, self._navigation.revision
        self._blocked_time = 0
        self._smooth(position)

    def _smooth(self, position):
        furthest = 0
        for i, point in enumerate(self._path[:8]):
            if abs(point[1] - position[1]) > 1e-4:
                break
            if self._navigation.can_walk(position, point, cache=False):
                furthest = i
        if furthest:
            del self._path[:furthest]

    def _make_parts(self):
        r, h = self.tuning.radius / 0.32, self.tuning.height / 0.45

        def box(position, size, material="plaster", emission=(0, 0, 0)):
            x, y, z = position
            w, height, depth = size
            return Box((x * r, y * h, z * r), (w * r, height * h, depth * r),
                       material=material, emission=emission, local_texture=True)

        parts = [box((0, 0.045, 0), (0.32, 0.09, 0.5)),
                 box((0, 0.105, -0.21), (0.28, 0.10, 0.12))]
        widths = (0.20, 0.30, 0.34, 0.30, 0.20)
        for i, (width, depth) in enumerate(zip(widths, (0.24, 0.34, 0.38, 0.34, 0.24))):
            parts.append(box((0, 0.14 + i * 0.06, 0.07), (width, 0.065, depth), "rust"))
        for side in (-1, 1):
            parts.append(box((side * 0.09, 0.23, -0.22), (0.025, 0.22, 0.025)))
            parts.append(box((side * 0.09, 0.36, -0.23), (0.065, 0.055, 0.045),
                             None, (2.2, 0.015, 0.005)))
            # Тёмная спираль на обеих сторонах ступенчатой раковины.
            for i in range(8):
                angle, radius = i * 0.9, 0.105 * (1 - i / 10)
                y, z = 0.26 + math.cos(angle) * radius, 0.07 + math.sin(angle) * radius
                layer = max(0, min(4, round((y - 0.14) / 0.06)))
                parts.append(box((side * (widths[layer] / 2 + 0.006), y, z),
                                 (0.012, 0.022, 0.022), "asphalt"))
        return tuple(parts)

    def _geometry(self):
        boxes = []
        for part in self._parts:
            rotated = part.rotated_around((0, 0, 0), self._yaw)
            boxes.append(replace(rotated, position=tuple(p + offset for p, offset in
                                                        zip(self.transform.position, rotated.position))))
        return tuple(boxes)
