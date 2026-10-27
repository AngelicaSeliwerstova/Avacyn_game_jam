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
    toggle_debug: int | None = None
    crouch_keys: tuple[int, ...] = ()
    interact: int | None = None
    zoom_mouse_button: int | None = None
    toggle_flashlight: int | None = None
    cycle_postprocess: int | None = None

    def __post_init__(self):
        if self.zoom_mouse_button is not None and self.zoom_mouse_button not in range(1, 6):
            raise ValueError("Zoom mouse button must be between 1 and 5")
