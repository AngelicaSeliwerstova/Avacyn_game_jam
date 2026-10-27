from dataclasses import dataclass, field
from typing import Protocol

from engine.input.state import InputState
from engine.scene.camera import Camera
from engine.scene.model import ModelComponent
from engine.scene.transform import Transform


@dataclass
class Entity:
    """Объект игры с мировым положением и необязательным описанием модели."""

    name: str
    transform: Transform = field(default_factory=Transform)
    model: ModelComponent | None = None


class ControlledEntity(Protocol):
    """Интерфейс управляемой сущности для игрового цикла движка."""

    camera: Camera

    @property
    def status_text(self) -> str: ...

    @property
    def aim_text(self) -> str: ...

    @property
    def debug_lines(self) -> tuple[str, ...]: ...

    def update(self, delta_time: float, inputs: InputState) -> None: ...


class SimulationSystem(Protocol):
    """Обновляемая система сцены без привязки движка к правилам игры."""

    def update(self, delta_time: float) -> None: ...
