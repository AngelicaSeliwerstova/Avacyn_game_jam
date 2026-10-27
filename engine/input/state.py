from dataclasses import dataclass


@dataclass(frozen=True)
class InputState:
    """Ввод кадра: направления, мышь, удержание бега/приседа и нажатие прыжка."""

    forward: float = 0.0
    right: float = 0.0
    mouse_delta: tuple[int, int] = (0, 0)
    sprint: bool = False
    jump: bool = False
    crouch: bool = False
