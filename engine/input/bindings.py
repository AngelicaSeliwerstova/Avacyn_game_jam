from dataclasses import dataclass


@dataclass(frozen=True)
class InputBindings:
    """Коды клавиш и кнопки мыши, передаваемые движку из настроек."""

    forward: int
    backward: int
    left: int
    right: int
    release_mouse: int
    capture_mouse_button: int
    toggle_fullscreen: int | None = None
    sprint_keys: tuple[int, ...] = ()
    jump: int | None = None
