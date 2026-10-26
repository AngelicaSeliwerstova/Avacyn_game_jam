from dataclasses import dataclass


@dataclass(frozen=True)
class InputState:
    """Ввод одного кадра: направления, мышь, удержание бега и нажатие прыжка."""

    forward: float = 0.0
    right: float = 0.0
    mouse_delta: tuple[int, int] = (0, 0)
    sprint: bool = False
    jump: bool = False
