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
from engine.scene.interaction import Interaction
from game.entities.appearance import create_character_model, create_doctor_model


class CompanionState(Enum):
    CHASE = "CHASE"
    WAITING = "WAITING"


@dataclass(frozen=True)
class CompanionSettings:
    speed: float = 3.8
    catch_up_speed: float = 8.0
    repath_interval: float = 0.25
    stop_distance: float = 1.4
    resume_distance: float = 2.0
    radius: float = 0.25
    height: float = 1.8
    step_height: float = 0.3

    def __post_init__(self):
        if (any(not math.isfinite(v) or v <= 0 for v in vars(self).values())
                or self.step_height >= self.height or self.resume_distance <= self.stop_distance):
            raise ValueError("Companion settings must be positive; resume_distance must exceed stop_distance")


class Companion(Entity):
    """An ally following a physical route without teleporting through obstacles."""

    def __init__(self, name: str, position, tuning: CompanionSettings | None = None, *,
                 following=True, display_name="Companion", dialogue=(), next_level=None,
                 appearance="player", story_actor=False):
        position = self._point(position)
        super().__init__(name=name, transform=Transform(position=position))
        self.tuning = tuning or CompanionSettings()
        self.body: CharacterBody | None = None
        self.state = CompanionState.CHASE
        self._yaw = 0.0
        self._path = []
        self._path_search = None
        self.path_complete = False
        self._path_timer = self._blocked_time = 0.0
        self._planned_goal = None
        self._planned_revision = -1
        self.following = following
        self.seated = appearance == "doctor" and not following
        if self.seated:
            self._yaw = 180.0
        self.display_name = display_name
        from game.dialogue import validate_dialogue
        self.dialogue = validate_dialogue(dialogue)
        self.next_level = next_level
        if next_level is not None and (not isinstance(next_level, str) or not next_level.strip()):
            raise ValueError("Conversation destination must be a nonempty level name")
        self.talk_requested = False
        self.story_actor = story_actor
        if appearance not in ("player", "doctor", "boxes"):
            raise ValueError("Companion appearance must be player, doctor or boxes")
        self.model = (create_doctor_model() if appearance == "doctor"
                      else create_character_model() if appearance == "player" else None)
        self._parts = self._make_parts()
        action = Interaction(display_name, "...", "Говорить", "talk") if self.dialogue or story_actor else None
        self.scene_object = SceneObject(name, {"default": ObjectState(self._geometry(), interaction=action)},
                                        entity=self, static_shadows=False)

    @staticmethod
    def _point(point):
        if len(point) != 3 or not all(math.isfinite(v) for v in point):
            raise ValueError("Companion positions need three finite world coordinates")
        return tuple(point)

    @property
    def path_length(self):
        return len(self._path)

    @property
    def remaining_path(self):
        return tuple(self._path)

    def bind(self, world, level, extra_obstacles=()):
        self.body = CharacterBody(
            self.transform.position, world, radius=self.tuning.radius, height=self.tuning.height,
            step_height=self.tuning.step_height, gravity=settings.GRAVITY,
            collision_max_step=settings.COLLISION_MAX_STEP, physics_step=settings.PHYSICS_STEP,
            camera_smoothing=settings.STAIR_CAMERA_SMOOTHING, jump_height=0,
        )
        self._graph = level.navigation
        self._navigation = NavigationTraversal(
            (box.collider for box in level.collision_boxes),
            tuple(obj for obj in level.objects if not hasattr(obj.entity, "body")) + extra_obstacles,
            level.floor_bounds,
            TraversalProfile(self.tuning.radius, self.tuning.height, self.tuning.step_height),
        )

    def update(self, delta_time, target_position, *, target_speed=0.0):
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Companion delta time must be finite and nonnegative")
        if not math.isfinite(target_speed) or target_speed < 0:
            raise ValueError("Companion target speed must be finite and nonnegative")
        if self.body is None:
            raise RuntimeError("Companion must be bound to a collision world before updating")
        target = self._point(target_position)
        position = tuple(self.body.position)
        if not self.following:
            if 0.01 < math.dist(position, target) < 4:
                self._yaw = math.degrees(math.atan2(position[0] - target[0], position[2] - target[2]))
            self.body.update(delta_time, glm.vec3(0))
            self._sync_pose()
            return
        self._path_timer -= delta_time
        distance_to_player = math.dist(position, target)
        threshold = self.tuning.resume_distance if self.state is CompanionState.WAITING else self.tuning.stop_distance
        if (distance_to_player <= threshold and abs(position[1] - target[1]) < 0.05
                and self._navigation.can_walk(position, target, cache=False)):
            self._path.clear()
            self._path_search = None
            self.state = CompanionState.WAITING
            self.body.update(delta_time, glm.vec3(0))
            self._sync_pose()
            return
        moved = self._planned_goal is None or math.dist(target, self._planned_goal) > 0.5
        changed = self._navigation.revision != self._planned_revision
        arrived_far = not self._path and self.path_complete and math.dist(position, target) > self.tuning.stop_distance
        if (self._path_timer <= 0
                and (changed or moved or (self._path_search is None
                                         and (arrived_far or self._blocked_time > 0.4 or not self._path)))):
            self._replan(position, target)
        if self._path_search is not None:
            self._path_search.advance(max_expansions=32, max_seconds=0.002)
            if self._path_search.done:
                result = self._path_search.result
                self._path, self.path_complete = list(result.points), result.complete
                self._path_search = None
                self._smooth(position)

        advanced = False
        while self._path and self._near(position, self._path[0], 0.14):
            self._path.pop(0)
            advanced = True
        if advanced:
            self._smooth(position)
        velocity = glm.vec3(0)
        self.state = CompanionState.WAITING
        if self._path:
            goal = self._path[0]
            final = self.path_complete and len(self._path) == 1
            following_target = (final and abs(position[1] - target[1]) < 0.01
                                and self._navigation.can_walk(position, target, cache=False))
            if following_target:
                goal = target
            delta = glm.vec3(goal) - self.body.position
            delta.y = 0
            distance = glm.length(delta)
            stopping = self.tuning.stop_distance if following_target else 0.08
            if distance > stopping and delta_time > 0:
                self._yaw = math.degrees(math.atan2(-delta.x, -delta.z))
                # Match the player's pace, then close any gap left by turns or stairs.
                pace = max(self.tuning.speed, target_speed)
                catch_up = max(0.0, distance_to_player - self.tuning.resume_distance) * 1.5
                speed = min(max(self.tuning.speed, self.tuning.catch_up_speed), pace + catch_up)
                velocity = delta / distance * min(speed, (distance - stopping) / delta_time)
            self.state = CompanionState.CHASE
        self.body.update(delta_time, velocity)
        if glm.length(velocity) > 0.01 and self.body.horizontal_speed < 0.02:
            self._blocked_time += delta_time
        else:
            self._blocked_time = 0.0
        self._sync_pose()

    def request_talk(self):
        if self.dialogue or self.story_actor:
            self.talk_requested = True

    def _sync_pose(self):
        pose = Transform(position=tuple(self.body.position), rotation=(0, self._yaw, 0))
        if pose != self.transform:
            self.transform = pose
            self.scene_object.set_geometry(self._geometry())

    def _near(self, a, b, distance):
        return math.hypot(a[0] - b[0], a[2] - b[2]) <= distance and abs(a[1] - b[1]) <= self.tuning.step_height + 0.01

    def _replan(self, position, target):
        clear = abs(position[1] - target[1]) < 0.01 and self._navigation.can_walk(position, target, cache=False)
        self._path_timer = self.tuning.repath_interval
        self._planned_goal, self._planned_revision = target, self._navigation.revision
        self._blocked_time = 0
        self._path_search = None
        if clear:
            self._path, self.path_complete = [target], True
            self._smooth(position)
        elif self._graph is not None:
            self._path_search = self._graph.start_path_search(position, target, self._navigation)
        else:
            self._path, self.path_complete = [], False

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
        if self.model is not None and self.model.source_path is not None:
            return (Box((0, self.tuning.height / 2, 0),
                        (self.tuning.radius * 2, self.tuning.height, self.tuning.radius * 2)),)
        return tuple(Box(position, size, color=color) for position, size, color in (
            ((0, 1.55, 0), (0.32, 0.36, 0.32), (0.75, 0.6, 0.48)),
            ((0, 1.05, 0), (0.42, 0.65, 0.26), (0.22, 0.36, 0.42)),
            ((-0.14, 0.36, 0), (0.18, 0.72, 0.22), (0.18, 0.2, 0.22)),
            ((0.14, 0.36, 0), (0.18, 0.72, 0.22), (0.18, 0.2, 0.22)),
        ))

    def _geometry(self):
        boxes = []
        for part in self._parts:
            rotated = part.rotated_around((0, 0, 0), self._yaw)
            boxes.append(replace(rotated, position=tuple(a + b for a, b in
                                                        zip(self.transform.position, rotated.position))))
        return tuple(boxes)
