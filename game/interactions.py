import math

from engine.raycasting.aabb import cast_ray
from engine.scene.box import Box
from engine.scene.camera import Camera
from engine.scene.object import SceneObject
from game.inventory import Inventory


class InteractionController:
    """Выбор видимого объекта и короткий ответ на одиночное нажатие действия."""

    def __init__(self, boxes: tuple[Box, ...], reach: float, message_seconds: float, key_label: str,
                 objects: tuple[SceneObject, ...] = (), inventory: Inventory | None = None):
        if any(not math.isfinite(value) or value <= 0 for value in (reach, message_seconds)):
            raise ValueError("Interaction reach and message duration must be positive")
        self._static_boxes = boxes
        self._objects = objects
        self._states = None
        self.inventory = inventory if inventory is not None else Inventory()
        self._refresh_objects()
        self._reach = reach
        self._message_seconds = message_seconds
        self._key_label = key_label
        self.focused: Box | SceneObject | None = None
        self._message = ""
        self._remaining = 0.0

    def update(self, delta_time: float, camera: Camera, pressed: bool = False):
        self._refresh_objects()
        self._remaining = max(0.0, self._remaining - delta_time)
        self.focused = None
        if self._targets:
            origin, direction = camera.position, camera.target - camera.position
            hit = cast_ray(origin, direction, self._target_colliders, self._reach)
            # Стены проверяем только при наведении на доступную цель.
            if hit is not None:
                blocker = cast_ray(origin, direction, self._colliders, hit.distance)
                if blocker is None or self._owners[blocker.index] is self._targets[hit.index]:
                    self.focused = self._targets[hit.index]
        if pressed and self.focused is not None:
            self._message = self._activate(self.focused)
            self._remaining = self._message_seconds
            if self.focused.interaction is None:
                self.focused = None

    def _refresh_objects(self):
        states = tuple(obj.current_state for obj in self._objects)
        if states == self._states:
            return
        entries = [(box, box) for box in self._static_boxes]
        entries.extend((box, obj) for obj in self._objects for box in obj.boxes)
        self._owners = tuple(owner for _, owner in entries)
        self._colliders = tuple(box.collider for box, _ in entries)
        targets = [(box, box) for box in self._static_boxes if box.interaction is not None]
        for obj in self._objects:
            if obj.interaction is not None:
                boxes = (obj.current_state.selection_box,) if obj.current_state.selection_box is not None else obj.boxes
                targets.extend((box, obj) for box in boxes)
        self._targets = tuple(owner for _, owner in targets)
        self._target_colliders = tuple(box.collider for box, _ in targets)
        self._states = states

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
