from dataclasses import dataclass, replace
import math
from types import MappingProxyType
from collections.abc import Callable

from engine.scene.box import Box
from engine.scene.interaction import Interaction


@dataclass(frozen=True)
class ObjectState:
    """Геометрия, столкновения и действие в одном состоянии объекта."""

    boxes: tuple[Box, ...] = ()
    collidable: bool = True
    interaction: Interaction | None = None
    selection_box: Box | None = None


class SceneObject:
    """Объект с именованными состояниями; правила переходов задаёт игра."""

    def __init__(self, name: str, states: dict[str, ObjectState], initial: str = "default",
                 transition_seconds: dict[str, float] | None = None,
                 rotation_pivot: tuple[float, float, float] | None = None):
        if not name.strip() or not states or any(not key.strip() for key in states):
            raise ValueError("Scene object and state names must not be empty")
        if initial not in states:
            raise ValueError(f"Unknown initial state: {initial!r}")
        self.name = name
        if rotation_pivot is not None and (len(rotation_pivot) != 3 or not all(math.isfinite(v) for v in rotation_pivot)):
            raise ValueError("Rotation pivot needs three finite coordinates")
        self.rotation_pivot = rotation_pivot
        self.motion_guard: Callable[[ObjectState], bool] | None = None
        self.states = MappingProxyType(dict(states))
        self._durations = dict(transition_seconds or {})
        if any(key not in states or not math.isfinite(value) or value <= 0
               for key, value in self._durations.items()):
            raise ValueError("Transitions need an existing target state and a positive finite duration")
        self._transition = None
        self._current_state = self.states[initial]
        self.set_state(initial)

    def set_state(self, name: str):
        if name not in self.states:
            raise ValueError(f"Unknown state {name!r} for object {self.name!r}")
        source, target = self.current_state, self.states[name]
        duration = self._durations.get(name, 0)
        if duration and source != target:
            if len(source.boxes) != len(target.boxes):
                raise ValueError("Animated states must have the same number of boxes")
            self._transition = source, target, duration, 0.0
            self._current_state = replace(source, interaction=None, selection_box=None)
        else:
            self._transition = None
            self._current_state = target
        self._state_name = name

    def update(self, delta_time: float):
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Object delta time must be finite and nonnegative")
        if self._transition is None:
            return
        source, target, duration, elapsed = self._transition
        remaining = min(delta_time, duration - elapsed)
        # Малые подшаги не позволяют двери перескочить через игрока при длинном кадре.
        while remaining > 1e-9:
            step = min(remaining, duration / 60)
            next_time = min(duration, elapsed + step)
            candidate = target if duration - next_time < 1e-9 else self._interpolate(source, target, next_time / duration)
            if self.motion_guard is not None and not self.motion_guard(candidate):
                break
            self._current_state = candidate
            elapsed = next_time
            remaining -= step
            if duration - elapsed < 1e-9:
                self._transition = None
                return
        self._transition = source, target, duration, elapsed

    def _interpolate(self, source, target, t):
        t = t * t * (3 - 2 * t)
        boxes = []
        for a, b in zip(source.boxes, target.boxes):
            angle = (b.yaw_degrees - a.yaw_degrees) * t
            if self.rotation_pivot is not None:
                pose = a.rotated_around(self.rotation_pivot, angle)
            else:
                pose = replace(a, position=tuple(x + (y - x) * t for x, y in zip(a.position, b.position)),
                               yaw_degrees=a.yaw_degrees + angle)
            boxes.append(replace(pose, size=tuple(x + (y - x) * t for x, y in zip(a.size, b.size))))
        return ObjectState(tuple(boxes), collidable=source.collidable)

    @property
    def state_name(self) -> str:
        return self._state_name

    @property
    def current_state(self) -> ObjectState:
        return self._current_state

    @property
    def boxes(self) -> tuple[Box, ...]:
        return self.current_state.boxes

    @property
    def interaction(self) -> Interaction | None:
        return self.current_state.interaction
