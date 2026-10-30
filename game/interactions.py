import math

from engine.raycasting.aabb import cast_ray
from engine.collision.obb import OBB
from engine.scene.box import Box
from engine.scene.camera import Camera
from engine.scene.object import SceneObject
from game.inventory import Inventory


class InteractionController:
    """Выбор видимого объекта и короткий ответ на одиночное нажатие действия."""

    _RAY_GRID_CELL_SIZE = 4.0
    _RAY_GRID_MARGIN = 1e-4

    def __init__(self, boxes: tuple[Box, ...], reach: float, message_seconds: float, key_label: str,
                 objects: tuple[SceneObject, ...] = (), inventory: Inventory | None = None,
                 aspect_ratio: float = 4 / 3):
        if any(not math.isfinite(value) or value <= 0 for value in (reach, message_seconds)):
            raise ValueError("Interaction reach and message duration must be positive")
        if not math.isfinite(aspect_ratio) or aspect_ratio <= 0:
            raise ValueError("Interaction view aspect ratio must be positive")
        self._static_boxes = boxes
        self._static_colliders = tuple(box.collider for box in boxes)
        self._static_spatial_index = self._build_spatial_index(
            self._static_colliders, 0,
        )
        self._static_targets = tuple(box for box in boxes if box.interaction is not None)
        self._static_target_colliders = tuple(box.collider for box in self._static_targets)
        self._objects = objects
        self._states = None
        self.inventory = inventory if inventory is not None else Inventory()
        self._refresh_objects()
        self._reach = reach
        self._aspect_ratio = aspect_ratio
        self._message_seconds = message_seconds
        self._key_label = key_label
        self.focused: Box | SceneObject | None = None
        self._message = ""
        self._remaining = 0.0

    def update(self, delta_time: float, camera: Camera, pressed: bool = False, reach_origin=None):
        self._refresh_objects()
        self._remaining = max(0.0, self._remaining - delta_time)
        self.focused = None
        if self._targets:
            origin = tuple(camera.position)
            reach_origin = tuple(origin if reach_origin is None else reach_origin)
            candidates = []
            for index, collider in enumerate(self._target_colliders):
                target = self._targets[index]
                if self._surface_distance(reach_origin, collider) > self._reach:
                    continue
                visible_score = self._visible_score(camera, origin, collider, target)
                if visible_score is not None:
                    alignment, view_distance = visible_score
                    candidates.append((alignment, self._surface_distance(reach_origin, collider),
                                       view_distance, target))
            if candidates:
                self.focused = min(candidates, key=lambda item: (item[0], item[1], item[2]))[3]
        if pressed and self.focused is not None:
            self._message = self._activate(self.focused)
            self._remaining = self._message_seconds
            if self.focused.interaction is None:
                self.focused = None

    def _visible_score(self, camera, origin, collider, target):
        direction = camera.target - camera.position
        direction = tuple(direction)
        length = math.hypot(*direction)
        forward = tuple(value / length for value in direction)
        world_up = (0.0, 1.0, 0.0)
        right = (
            forward[1] * world_up[2] - forward[2] * world_up[1],
            forward[2] * world_up[0] - forward[0] * world_up[2],
            forward[0] * world_up[1] - forward[1] * world_up[0],
        )
        right_length = math.hypot(*right)
        right = tuple(value / right_length for value in right)
        up = (
            right[1] * forward[2] - right[2] * forward[1],
            right[2] * forward[0] - right[0] * forward[2],
            right[0] * forward[1] - right[1] * forward[0],
        )
        vertical_tangent = math.tan(math.radians(camera.fov_degrees) / 2)
        horizontal_tangent = vertical_tangent * self._aspect_ratio
        nearest = None
        for point in self._box_points(collider):
            relative = tuple(value - start for value, start in zip(point, origin))
            depth = sum(value * axis for value, axis in zip(relative, forward))
            if depth <= camera.near or depth >= camera.far:
                continue
            if (abs(sum(value * axis for value, axis in zip(relative, right))) > depth * horizontal_tangent
                    or abs(sum(value * axis for value, axis in zip(relative, up))) > depth * vertical_tangent):
                continue
            distance = math.hypot(*relative)
            collider_indices = self._ray_colliders(origin, relative, distance + 1e-5)
            if collider_indices:
                nearby_colliders = tuple(self._colliders[index] for index in collider_indices)
                blocker = cast_ray(origin, relative, nearby_colliders, distance + 1e-5)
                if blocker is not None and self._owners[collider_indices[blocker.index]] is not target:
                    continue
            horizontal = abs(sum(value * axis for value, axis in zip(relative, right))
                             / (depth * horizontal_tangent))
            vertical = abs(sum(value * axis for value, axis in zip(relative, up))
                           / (depth * vertical_tangent))
            candidate = (horizontal * horizontal + vertical * vertical, distance)
            if nearest is None or candidate < nearest:
                nearest = candidate
        return nearest

    @staticmethod
    def _box_points(collider):
        footprint = collider.footprint
        points = []
        if isinstance(footprint, OBB):
            angle = math.radians(footprint.yaw_degrees)
            cosine, sine = math.cos(angle), math.sin(angle)
            center_y = (collider.bottom + collider.top) / 2
            for local_x in (-footprint.half_width, footprint.half_width):
                for local_z in (-footprint.half_depth, footprint.half_depth):
                    x = footprint.x + cosine * local_x + sine * local_z
                    z = footprint.z - sine * local_x + cosine * local_z
                    points.extend((x, y, z) for y in (collider.bottom, center_y, collider.top))
            points.extend((
                (footprint.x, collider.bottom, footprint.z),
                (footprint.x, center_y, footprint.z),
                (footprint.x, collider.top, footprint.z),
            ))
            return tuple(points)
        center_x = (footprint.min_x + footprint.max_x) / 2
        center_y = (collider.bottom + collider.top) / 2
        center_z = (footprint.min_z + footprint.max_z) / 2
        for x in (footprint.min_x, footprint.max_x):
            for z in (footprint.min_z, footprint.max_z):
                points.extend((x, y, z) for y in (collider.bottom, center_y, collider.top))
        points.extend((
            (center_x, collider.bottom, center_z),
            (center_x, center_y, center_z),
            (center_x, collider.top, center_z),
        ))
        return tuple(points)

    @staticmethod
    def _surface_distance(point, collider):
        footprint = collider.footprint
        if isinstance(footprint, OBB):
            local_x, local_z = footprint.local_point(point[0], point[2])
            local_x = max(-footprint.half_width, min(footprint.half_width, local_x))
            local_z = max(-footprint.half_depth, min(footprint.half_depth, local_z))
            angle = math.radians(footprint.yaw_degrees)
            cosine, sine = math.cos(angle), math.sin(angle)
            closest_x = footprint.x + cosine * local_x + sine * local_z
            closest_z = footprint.z - sine * local_x + cosine * local_z
        else:
            closest_x = max(footprint.min_x, min(footprint.max_x, point[0]))
            closest_z = max(footprint.min_z, min(footprint.max_z, point[2]))
        closest_y = max(collider.bottom, min(collider.top, point[1]))
        return math.dist(point, (closest_x, closest_y, closest_z))

    def _refresh_objects(self):
        states = tuple(obj.current_state for obj in self._objects)
        if states == self._states:
            return
        entries = [(box, obj) for obj in self._objects for box in obj.boxes]
        self._owners = self._static_boxes + tuple(owner for _, owner in entries)
        dynamic_colliders = tuple(box.collider for box, _ in entries)
        self._colliders = self._static_colliders + dynamic_colliders
        self._dynamic_spatial_index = self._build_spatial_index(
            dynamic_colliders, len(self._static_colliders),
        )
        targets = []
        for obj in self._objects:
            if obj.interaction is not None:
                boxes = (obj.current_state.selection_box,) if obj.current_state.selection_box is not None else obj.boxes
                targets.extend((box, obj) for box in boxes)
        self._targets = self._static_targets + tuple(owner for _, owner in targets)
        self._target_colliders = self._static_target_colliders + tuple(box.collider for box, _ in targets)
        self._states = states

    def _build_spatial_index(self, colliders, offset):
        index = {}
        cell_size = self._RAY_GRID_CELL_SIZE
        margin = self._RAY_GRID_MARGIN
        for collider_index, collider in enumerate(colliders, offset):
            footprint = collider.footprint
            min_x = math.floor((footprint.min_x - margin) / cell_size)
            max_x = math.floor((footprint.max_x + margin) / cell_size)
            min_z = math.floor((footprint.min_z - margin) / cell_size)
            max_z = math.floor((footprint.max_z + margin) / cell_size)
            for cell_x in range(min_x, max_x + 1):
                for cell_z in range(min_z, max_z + 1):
                    index.setdefault((cell_x, cell_z), []).append(collider_index)
        return index

    def _ray_colliders(self, origin, direction, distance):
        cell_size = self._RAY_GRID_CELL_SIZE
        margin = self._RAY_GRID_MARGIN
        end_x = origin[0] + direction[0] * distance
        end_z = origin[2] + direction[2] * distance
        min_x = math.floor((min(origin[0], end_x) - margin) / cell_size)
        max_x = math.floor((max(origin[0], end_x) + margin) / cell_size)
        min_z = math.floor((min(origin[2], end_z) - margin) / cell_size)
        max_z = math.floor((max(origin[2], end_z) + margin) / cell_size)
        indices = set()
        for cell_x in range(min_x, max_x + 1):
            for cell_z in range(min_z, max_z + 1):
                indices.update(self._static_spatial_index.get((cell_x, cell_z), ()))
                indices.update(self._dynamic_spatial_index.get((cell_x, cell_z), ()))
        return tuple(sorted(indices))

    def _activate(self, target: Box | SceneObject) -> str:
        action = target.interaction
        if action.command == "inspect":
            return action.message
        if not isinstance(target, SceneObject):
            raise ValueError("Stateful interactions require a SceneObject")
        if action.command == "pickup_key":
            self.inventory.add_key(action.argument, action.name)
            target.set_state("collected")
        elif action.command == "unlock_door":
            if not self.inventory.has_key(action.argument):
                return "Locked. Find the matching key."
            target.set_state("open")
        else:
            raise ValueError(f"Unknown interaction command: {action.command}")
        return action.message

    @property
    def text(self) -> str:
        lines = []
        if self.focused is not None:
            action = self.focused.interaction
            lines.append(f"[{self._key_label}] {action.action} - {action.name}")
        if self._remaining > 0:
            lines.append(self._message)
        return "\n".join(lines)
