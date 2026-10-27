from dataclasses import dataclass


@dataclass(frozen=True)
class DebugPath:
    """Ломаная в мировых координатах для просмотра в режиме разработчика."""

    points: tuple[tuple[float, float, float], ...]
    color: tuple[float, float, float] = (1.0, 0.08, 0.04)
