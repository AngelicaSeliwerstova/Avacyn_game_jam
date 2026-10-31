from dataclasses import dataclass
from collections.abc import Callable

from engine.debug.geometry import DebugPath
from engine.particles.snow import Snowfall
from engine.scene.entity import ControlledEntity, SimulationSystem
from engine.scene.level import Level
from engine.scene.session import Session


@dataclass
class RuntimeScene:
    """Все зависимости локации заменяются вместе, в существующем окне."""

    level: Level
    player: ControlledEntity
    session: Session
    systems: tuple[SimulationSystem, ...] = ()
    snow: Snowfall | None = None
    debug_paths: Callable[[], tuple[DebugPath, ...]] | None = None
