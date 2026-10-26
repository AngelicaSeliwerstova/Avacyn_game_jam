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
)
