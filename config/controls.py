import pygame

from engine.input.bindings import InputBindings


INPUT_BINDINGS = InputBindings(
    forward=pygame.K_w,
    backward=pygame.K_s,
    left=pygame.K_a,
    right=pygame.K_d,
    release_mouse=pygame.K_ESCAPE,
    capture_mouse_button=1,  # Левая кнопка мыши.
    toggle_fullscreen=pygame.K_F11,
    sprint_keys=(pygame.K_LSHIFT, pygame.K_RSHIFT),
    jump=pygame.K_SPACE,
    toggle_debug=pygame.K_F3,
    cycle_postprocess=pygame.K_F5,
    crouch_keys=(pygame.K_LCTRL, pygame.K_RCTRL),
    interact=pygame.K_e,
    zoom_mouse_button=3,  # Удержание правой кнопки мыши.
    toggle_flashlight=pygame.K_f,
    look_back=pygame.K_q,
    toggle_camera_editor=pygame.K_F6,
    add_camera=pygame.K_F7,
    delete_camera=pygame.K_DELETE,
    add_object=pygame.K_F9,
    cycle_creator_material=pygame.K_F8,
    creator_up=pygame.K_SPACE,
    add_creator_light=pygame.K_F10,
    recalculate_shadows=pygame.K_F12,
    cycle_creator_light_flicker=pygame.K_F4,
)
