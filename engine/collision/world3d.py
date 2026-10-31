from collections import defaultdict
from collections.abc import Iterable
import math

import glm

from engine.collision.aabb import AABB
from engine.collision.aabb3d import AABB3D
from engine.collision.world import CollisionWorld
from engine.scene.object import SceneObject


class CollisionWorld3D:
    """Движение вертикального цилиндра среди блоков с заданной высотой нижнего пола."""

    EPSILON = 1e-5
    _GRID_CELL_SIZE = 4.0

    def __init__(self, colliders: Iterable[AABB3D], bounds: AABB | None = None, ground_height: float = 0.0,
                 objects: tuple[SceneObject, ...] = ()):
        if not math.isfinite(ground_height):
            raise ValueError("Ground height must be finite")
        self._static_colliders = tuple(colliders)
        self._creator_colliders = ()
        self._objects = objects
        self._object_states = None
        self._colliders = self._static_colliders
        self._collider_grid = {}
        self.bounds = bounds
        self.ground_height = ground_height

    @property
    def colliders(self) -> tuple[AABB3D, ...]:
        states = tuple(obj.current_state for obj in self._objects)
        if states != self._object_states:
            self._colliders = self._static_colliders + tuple(
                self._creator_colliders
            ) + tuple(box.collider for state in states if state.collidable for box in state.boxes)
            self._object_states = states
            self._rebuild_collider_grid()
        return self._colliders

    def set_creator_colliders(self, boxes) -> None:
        colliders = tuple(box.collider for box in boxes)
        if colliders == self._creator_colliders:
            return
        self._creator_colliders = colliders
        self._object_states = None

    def _rebuild_collider_grid(self):
        grid = defaultdict(list)
        for index, box in enumerate(self._colliders):
            footprint = box.footprint
            min_x = math.floor(footprint.min_x / self._GRID_CELL_SIZE)
            max_x = math.floor(footprint.max_x / self._GRID_CELL_SIZE)
            min_z = math.floor(footprint.min_z / self._GRID_CELL_SIZE)
            max_z = math.floor(footprint.max_z / self._GRID_CELL_SIZE)
            for cell_x in range(min_x, max_x + 1):
                for cell_z in range(min_z, max_z + 1):
                    grid[(cell_x, cell_z)].append(index)
        self._collider_grid = {key: tuple(indices) for key, indices in grid.items()}

    def _nearby_colliders(self, min_x: float, max_x: float, min_z: float, max_z: float):
        colliders = self.colliders
        indices = set()
        for cell_x in range(math.floor(min_x / self._GRID_CELL_SIZE),
                            math.floor(max_x / self._GRID_CELL_SIZE) + 1):
            for cell_z in range(math.floor(min_z / self._GRID_CELL_SIZE),
                                math.floor(max_z / self._GRID_CELL_SIZE) + 1):
                indices.update(self._collider_grid.get((cell_x, cell_z), ()))
        return (colliders[index] for index in sorted(indices))

    def _horizontal_world(self, feet: float, height: float, x: float, z: float,
                          dx: float, dz: float, radius: float) -> CollisionWorld:
        nearby = self._nearby_colliders(
            min(x, x + dx) - radius, max(x, x + dx) + radius,
            min(z, z + dz) - radius, max(z, z + dz) + radius,
        )
        return CollisionWorld((
            box.footprint for box in nearby
            if box.bottom < feet + height - self.EPSILON and box.top > feet + self.EPSILON
        ), self.bounds)

    def is_blocked(self, position: glm.vec3, radius: float, height: float) -> bool:
        if position.y < self.ground_height - self.EPSILON:
            return True
        world = self._horizontal_world(
            position.y, height, position.x, position.z, 0, 0, radius,
        )
        return world.is_blocked(position, radius)

    def support_height(self, position: glm.vec3, radius: float, limit: float) -> float:
        return max(self.ground_height, max((
            box.top for box in self._nearby_colliders(
                position.x - radius, position.x + radius,
                position.z - radius, position.z + radius,
            )
            if box.top <= limit + self.EPSILON
            and box.footprint.intersects_circle(position.x, position.z, radius)
        ), default=self.ground_height))

    def move_horizontal(self, position: glm.vec3, displacement: glm.vec3,
                        radius: float, height: float, max_step: float,
                        step_height: float, grounded: bool) -> glm.vec3:
        distance = math.hypot(displacement.x, displacement.z)
        steps = max(1, math.ceil(distance / min(max_step, radius * 0.5)))
        delta = glm.vec3(displacement.x / steps, 0, displacement.z / steps)
        result = glm.vec3(position)
        for _ in range(steps):
            desired = result + delta
            world = self._horizontal_world(
                result.y, height, result.x, result.z, delta.x, delta.z, radius,
            )
            flat = world.move(result, delta, radius, max_step)
            blocked = glm.length(flat - desired) > self.EPSILON
            if grounded and blocked and step_height > 0:
                top = self.support_height(desired, radius, result.y + step_height)
                if top > result.y + self.EPSILON:
                    raised = glm.vec3(result.x, top, result.z)
                    # Подъём требует места над головой и в начале, и в конце шага.
                    if not self.is_blocked(raised, radius, height):
                        raised_world = self._horizontal_world(
                            top, height, raised.x, raised.z, delta.x, delta.z, radius,
                        )
                        raised = raised_world.move(raised, delta, radius, max_step)
                        destination = glm.vec3(desired.x, top, desired.z)
                        if glm.length(raised - destination) <= self.EPSILON:
                            flat = raised
            result = flat
            if grounded:
                support = self.support_height(result, radius, result.y)
                if result.y - support <= step_height + self.EPSILON:
                    result.y = support
                else:
                    # После края нельзя подняться на следующую ступеньку в воздухе.
                    grounded = False
        return result

    def move_vertical(self, position: glm.vec3, delta: float,
                      radius: float, height: float) -> tuple[glm.vec3, bool]:
        result = glm.vec3(position)
        destination = float(position.y) + delta
        hit = False
        if delta <= 0:
            support = self.support_height(position, radius, position.y)
            if destination <= support:
                destination = support
                hit = True
        else:
            for box in self._nearby_colliders(
                position.x - radius, position.x + radius,
                position.z - radius, position.z + radius,
            ):
                if (box.bottom >= position.y + height - self.EPSILON
                        and box.footprint.intersects_circle(position.x, position.z, radius)
                        and destination + height >= box.bottom):
                    destination = min(destination, box.bottom - height)
                    hit = True
        result.y = destination
        return result, hit
