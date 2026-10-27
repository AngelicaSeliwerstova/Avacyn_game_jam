import math

from engine.raycasting.aabb import cast_ray
from engine.scene.box import Box
from engine.scene.camera import Camera


class InteractionController:
    """Выбор видимого объекта и короткий ответ на одиночное нажатие действия."""

    def __init__(self, boxes: tuple[Box, ...], reach: float, message_seconds: float, key_label: str):
        if any(not math.isfinite(value) or value <= 0 for value in (reach, message_seconds)):
            raise ValueError("Interaction reach and message duration must be positive")
        self._boxes = boxes
        self._colliders = tuple(box.collider for box in boxes)
        self._targets = tuple(box for box in boxes if box.interaction is not None)
        self._target_colliders = tuple(box.collider for box in self._targets)
        self._reach = reach
        self._message_seconds = message_seconds
        self._key_label = key_label
        self.focused: Box | None = None
        self._message = ""
        self._remaining = 0.0

    def update(self, delta_time: float, camera: Camera, pressed: bool = False):
        self._remaining = max(0.0, self._remaining - delta_time)
        self.focused = None
        if self._targets:
            origin, direction = camera.position, camera.target - camera.position
            hit = cast_ray(origin, direction, self._target_colliders, self._reach)
            # Стены проверяем только при наведении на доступную цель.
            if hit is not None:
                blocker = cast_ray(origin, direction, self._colliders, hit.distance)
                if blocker is not None and self._boxes[blocker.index] is self._targets[hit.index]:
                    self.focused = self._targets[hit.index]
        if pressed and self.focused is not None:
            self._message = self.focused.interaction.message
            self._remaining = self._message_seconds

    @property
    def text(self) -> str:
        lines = []
        if self.focused is not None:
            action = self.focused.interaction
            lines.append(f"[{self._key_label}] {action.action} - {action.name}")
        if self._remaining > 0:
            lines.append(self._message)
        return "\n".join(lines)
