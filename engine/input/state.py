from dataclasses import dataclass


@dataclass(frozen=True)
class InputState:
    """Ввод кадра: направления, мышь, бег/присед/зум, нажатия прыжка и действия."""

    forward: float = 0.0
    right: float = 0.0
    mouse_delta: tuple[int, int] = (0, 0)
    sprint: bool = False
    jump: bool = False
    crouch: bool = False
    interact: bool = False
    zoom: bool = False
    toggle_flashlight: bool = False
    look_back: bool = False
    toggle_camera_editor: bool = False
    add_camera: bool = False
    delete_camera: bool = False
    add_object: bool = False
    cycle_creator_material: bool = False
    creator_up: bool = False
    add_creator_light: bool = False
    recalculate_shadows: bool = False
