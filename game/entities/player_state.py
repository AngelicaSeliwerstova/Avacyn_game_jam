from enum import Enum


class MovementState(Enum):
    """Наблюдаемое состояние движения, вычисляемое из результата физики."""

    IDLE = "IDLE"
    WALKING = "WALKING"
    RUNNING = "RUNNING"
    RISING = "RISING"
    FALLING = "FALLING"
