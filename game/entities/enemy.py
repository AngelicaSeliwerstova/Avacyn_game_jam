from dataclasses import dataclass, replace
from enum import Enum
import math

import glm

from config import settings
from engine.physics.character import CharacterBody
from engine.raycasting.aabb import cast_ray
from engine.scene.box import Box
from engine.scene.entity import Entity
from engine.scene.object import ObjectState, SceneObject
from engine.scene.transform import Transform


class EnemyState(Enum):
    IDLE = "IDLE"
    PATROL = "PATROL"
    CHASE = "CHASE"
    SEARCH = "SEARCH"


@dataclass(frozen=True)
class EnemySettings:
    patrol_speed: float = settings.ENEMY_PATROL_SPEED
    chase_speed: float = settings.ENEMY_CHASE_SPEED
    sight_range: float = settings.ENEMY_SIGHT_RANGE
    view_angle: float = settings.ENEMY_VIEW_ANGLE
    memory_seconds: float = settings.ENEMY_MEMORY_SECONDS
    vision_interval: float = settings.ENEMY_VISION_INTERVAL
    stop_distance: float = settings.ENEMY_STOP_DISTANCE
    radius: float = settings.ENEMY_RADIUS
    height: float = settings.ENEMY_HEIGHT

    def __post_init__(self):
        if any(not math.isfinite(v) or v <= 0 for v in vars(self).values()) or self.view_angle > 360:
            raise ValueError("Enemy settings must be positive and finite; view_angle must be at most 360")
        if self.height <= settings.PLAYER_STEP_HEIGHT:
            raise ValueError("Enemy height must exceed the step height")


class Enemy(Entity):
    """Патруль, видимость игрока и короткая память о последней замеченной позиции."""

    def __init__(self, name: str, position, patrol=(), tuning: EnemySettings | None = None):
        position = self._point(position)
        super().__init__(name=name, transform=Transform(position=position))
        self.tuning = tuning or EnemySettings()
        self.patrol = tuple(self._point(point) for point in patrol) or (position,)
        if any(abs(point[1] - position[1]) > 0.1 for point in self.patrol):
            raise ValueError("Enemy patrol points must be on the same floor as its spawn")
        self.body: CharacterBody | None = None
        self.state = EnemyState.PATROL if len(self.patrol) > 1 else EnemyState.IDLE
        self._waypoint = 1 if len(self.patrol) > 1 and math.dist(position, self.patrol[0]) < 0.2 else 0
        self._memory = self._vision_timer = 0.0
        self._visible = False
        self._last_seen = glm.vec3(position)
        self._yaw = 0.0
        self._face(glm.vec3(self.patrol[self._waypoint]) - glm.vec3(position))
        self.transform = Transform(position=position, rotation=(0, self._yaw, 0))
        self._parts = self._make_parts()
        self.scene_object = SceneObject(name, {"default": ObjectState(self._geometry())},
                                        entity=self, static_shadows=False)

    @staticmethod
    def _point(point):
        if len(point) != 3 or not all(math.isfinite(v) for v in point):
            raise ValueError("Enemy positions need three finite world coordinates")
        return tuple(point)

    def bind(self, world, level):
        self.body = CharacterBody(
            self.transform.position, world, radius=self.tuning.radius, height=self.tuning.height,
            step_height=settings.PLAYER_STEP_HEIGHT, gravity=settings.GRAVITY,
            collision_max_step=settings.COLLISION_MAX_STEP, physics_step=settings.PHYSICS_STEP,
            camera_smoothing=settings.STAIR_CAMERA_SMOOTHING, jump_height=0,
        )
        self._static_sight = tuple(box.collider for box in level.boxes + level.decorations)
        self._sight_objects = tuple(obj for obj in level.objects if obj is not self.scene_object)

    def update(self, delta_time, target_position, target_eye):
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Enemy delta time must be finite and nonnegative")
        if self.body is None:
            raise RuntimeError("Enemy must be bound to a collision world before updating")
        self._memory = max(0.0, self._memory - delta_time)
        self._vision_timer -= delta_time
        if self._vision_timer <= 0:
            self._vision_timer = self.tuning.vision_interval
            self._visible = self._can_see(target_eye)
            if self._visible:
                self._last_seen = glm.vec3(target_position)
                self._memory = self.tuning.memory_seconds

        if self._memory > 0:
            self.state = EnemyState.CHASE if self._visible else EnemyState.SEARCH
            goal, speed = self._last_seen, self.tuning.chase_speed
            stopping = self.tuning.stop_distance if self._visible else 0.2
        else:
            goal = glm.vec3(self.patrol[self._waypoint])
            if self._horizontal_distance(goal, self.body.position) < 0.2 and len(self.patrol) > 1:
                self._waypoint = (self._waypoint + 1) % len(self.patrol)
                goal = glm.vec3(self.patrol[self._waypoint])
            self.state = EnemyState.PATROL
            speed, stopping = self.tuning.patrol_speed, 0.15

        delta = goal - self.body.position
        delta.y = 0
        distance = glm.length(delta)
        velocity = glm.vec3(0)
        if distance > stopping and delta_time > 0:
            self._face(delta)
            speed = min(speed, (distance - stopping) / delta_time)
            velocity = delta / distance * speed
        elif self._memory <= 0 and len(self.patrol) == 1:
            self.state = EnemyState.IDLE
        self.body.update(delta_time, velocity)
        pose = Transform(position=tuple(self.body.position), rotation=(0, self._yaw, 0))
        if pose != self.transform:
            self.transform = pose
            self.scene_object.set_geometry(self._geometry())

    def _can_see(self, target_eye):
        origin = self.body.eye_position(self.tuning.height * 0.87)
        delta = glm.vec3(target_eye) - origin
        distance = glm.length(delta)
        if distance > self.tuning.sight_range:
            return False
        if distance < 1e-5:
            return True
        horizontal = math.hypot(delta.x, delta.z)
        if self._memory <= 0 and horizontal > 1e-5:
            yaw = math.radians(self._yaw)
            facing = (-math.sin(yaw) * delta.x - math.cos(yaw) * delta.z) / horizontal
            if facing < math.cos(math.radians(self.tuning.view_angle / 2)):
                return False
        colliders = self._static_sight + tuple(box.collider for obj in self._sight_objects for box in obj.boxes)
        return cast_ray(tuple(origin), tuple(delta), colliders, max(0, distance - 0.05)) is None

    @staticmethod
    def _horizontal_distance(a, b):
        return math.hypot(a.x - b.x, a.z - b.z)

    def _face(self, direction):
        if math.hypot(direction.x, direction.z) > 1e-5:
            self._yaw = math.degrees(math.atan2(-direction.x, -direction.z))

    def _make_parts(self):
        h, r = self.tuning.height / 1.75, self.tuning.radius / 0.4
        parts = (
            ((0, 1.55, 0), (0.34, 0.34, 0.34), "concrete"),
            ((0, 1.0, 0), (0.48, 0.72, 0.28), "plaster"),
            ((-0.30, 1.0, 0), (0.14, 0.65, 0.2), "plaster"),
            ((0.30, 1.0, 0), (0.14, 0.65, 0.2), "plaster"),
            ((-0.13, 0.32, 0), (0.18, 0.64, 0.22), "rust"),
            ((0.13, 0.32, 0), (0.18, 0.64, 0.22), "rust"),
        )
        boxes = tuple(Box((x * r, y * h, z * r), (w * r, height * h, d * r),
                          material=material, local_texture=True)
                      for (x, y, z), (w, height, d), material in parts)
        eyes = tuple(Box((x * r, 1.59 * h, -0.185 * r), (0.05 * r, 0.04 * h, 0.025 * r),
                         emission=(1.2, 0.04, 0.01), local_texture=True) for x in (-0.075, 0.075))
        return boxes + eyes

    def _geometry(self):
        boxes = []
        for part in self._parts:
            rotated = part.rotated_around((0, 0, 0), self._yaw)
            boxes.append(replace(rotated, position=tuple(p + offset for p, offset in
                                                        zip(self.transform.position, rotated.position))))
        return tuple(boxes)
