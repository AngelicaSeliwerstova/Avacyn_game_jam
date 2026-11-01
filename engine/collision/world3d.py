from collections import defaultdict
from collections.abc import Iterable
import math

import glm

from engine.collision.aabb import AABB
from engine.collision.aabb3d import AABB3D
from engine.collision.world import CollisionWorld
from engine.scene.object import SceneObject
from engine.raycasting.aabb import cast_ray


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
        self._fixed_dirty = True
        self._dynamic_colliders = ()
        self._dynamic_grid = {}
        self._object_geometry = {}
        self.bounds = bounds
        self.ground_height = ground_height

    @property
    def colliders(self) -> tuple[AABB3D, ...]:
        states = tuple(obj.current_state for obj in self._objects)
        if self._fixed_dirty:
            self._fixed_colliders = self._static_colliders + self._creator_colliders
            self._collider_grid = self._build_grid(self._fixed_colliders)
            self._fixed_dirty = False
        if states != self._object_states:
            geometry = {}
            dynamic = []
            for obj, state in zip(self._objects, states):
                if not state.collidable:
                    continue
                previous = self._object_geometry.get(obj)
                boxes = state.boxes
                colliders = (previous[1] if previous is not None and previous[0] is boxes
                             else tuple(box.collider for box in boxes))
                geometry[obj] = boxes, colliders
                dynamic.extend(colliders)
            self._object_geometry = geometry
            self._dynamic_colliders = tuple(dynamic)
            self._dynamic_grid = self._build_grid(self._dynamic_colliders)
            self._colliders = self._fixed_colliders + self._dynamic_colliders
            self._object_states = states
        return self._colliders

    def set_static_colliders(self, colliders) -> None:
        colliders = tuple(colliders)
        if colliders != self._static_colliders:
            self._static_colliders = colliders
            self._object_states = None
            self._fixed_dirty = True

    def set_creator_colliders(self, boxes) -> None:
        colliders = tuple(box.collider for box in boxes)
        if colliders == self._creator_colliders:
            return
        self._creator_colliders = colliders
        self._object_states = None
        self._fixed_dirty = True

    def _build_grid(self, colliders):
        grid = defaultdict(list)
        for index, box in enumerate(colliders):
            footprint = box.footprint
            min_x = math.floor(footprint.min_x / self._GRID_CELL_SIZE)
            max_x = math.floor(footprint.max_x / self._GRID_CELL_SIZE)
            min_z = math.floor(footprint.min_z / self._GRID_CELL_SIZE)
            max_z = math.floor(footprint.max_z / self._GRID_CELL_SIZE)
            for cell_x in range(min_x, max_x + 1):
                for cell_z in range(min_z, max_z + 1):
                    grid[(cell_x, cell_z)].append(index)
        return {key: tuple(indices) for key, indices in grid.items()}

    def _nearby_colliders(self, min_x: float, max_x: float, min_z: float, max_z: float):
        self.colliders
        indices, dynamic_indices = set(), set()
        for cell_x in range(math.floor(min_x / self._GRID_CELL_SIZE),
                            math.floor(max_x / self._GRID_CELL_SIZE) + 1):
            for cell_z in range(math.floor(min_z / self._GRID_CELL_SIZE),
                                math.floor(max_z / self._GRID_CELL_SIZE) + 1):
                indices.update(self._collider_grid.get((cell_x, cell_z), ()))
                dynamic_indices.update(self._dynamic_grid.get((cell_x, cell_z), ()))
        for index in sorted(indices):
            yield self._fixed_colliders[index]
        for index in sorted(dynamic_indices):
            yield self._dynamic_colliders[index]

    def is_occluded(self, origin, target, margin=0.05):
        direction = tuple(b - a for a, b in zip(origin, target))
        distance = math.hypot(*direction) - margin
        if distance <= 0:
            return False
        nearby = self._nearby_colliders(min(origin[0], target[0]), max(origin[0], target[0]),
                                        min(origin[2], target[2]), max(origin[2], target[2]))
        hit = cast_ray(origin, direction, nearby, distance)
        return hit is not None and hit.distance < distance

    def _horizontal_world(self, feet: float, height: float, x: float, z: float,
                          dx: float, dz: float, radius: float) -> CollisionWorld:
        # Projecting along a slanted wall can leave the original X/Z rectangle.
        # Include the entire possible slide, including neighbouring grid cells.
        padding = radius + math.hypot(dx, dz)
        nearby = self._nearby_colliders(
            min(x, x + dx) - padding, max(x, x + dx) + padding,
            min(z, z + dz) - padding, max(z, z + dz) + padding,
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
        if distance == 0:
            return glm.vec3(position)
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
                    if not self.is_blocked(raised, max(0, radius - self.EPSILON), height):
                        raised_world = self._horizontal_world(
                            top, height, raised.x, raised.z, delta.x, delta.z, radius,
                        )
                        raised = raised_world.move(raised, delta, radius, max_step)
                        destination = glm.vec3(desired.x, top, desired.z)
                        raised_progress = (raised.x - result.x) * delta.x + (raised.z - result.z) * delta.z
                        flat_progress = (flat.x - result.x) * delta.x + (flat.z - result.z) * delta.z
                        # A stair and a rail may be hit in the same substep.
                        # Accept the useful raised slide even if the rail prevents
                        # reaching the full requested displacement.
                        if (glm.length(raised - destination) <= self.EPSILON
                                or raised_progress > flat_progress + self.EPSILON ** 2):
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
