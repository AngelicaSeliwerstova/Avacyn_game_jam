from dataclasses import dataclass
from types import MappingProxyType

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

    def __init__(self, name: str, states: dict[str, ObjectState], initial: str = "default"):
        if not name.strip() or not states or any(not key.strip() for key in states):
            raise ValueError("Scene object and state names must not be empty")
        self.name = name
        self.states = MappingProxyType(dict(states))
        self.set_state(initial)

    def set_state(self, name: str):
        if name not in self.states:
            raise ValueError(f"Unknown state {name!r} for object {self.name!r}")
        self._state_name = name

    @property
    def state_name(self) -> str:
        return self._state_name

    @property
    def current_state(self) -> ObjectState:
        return self.states[self._state_name]

    @property
    def boxes(self) -> tuple[Box, ...]:
        return self.current_state.boxes

    @property
    def interaction(self) -> Interaction | None:
        return self.current_state.interaction
