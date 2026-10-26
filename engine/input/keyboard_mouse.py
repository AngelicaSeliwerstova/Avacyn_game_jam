import pygame

from engine.input.bindings import InputBindings


class KeyboardMouse:
    """Читает ввод и освобождает мышь при потере фокуса или по Esc."""

    def __init__(self, bindings: InputBindings):
        self._bindings = bindings
        self._focused = bool(pygame.key.get_focused())
        self._captured = False
        self._discard_mouse_delta = True
        self._set_capture(self._focused)

    def _set_capture(self, captured: bool):
        pygame.event.set_grab(captured)
        pygame.mouse.set_visible(not captured)
        pygame.mouse.get_rel()
        self._captured = captured
        # Первый отсчёт после захвата может содержать смещение курсора ОС.
        self._discard_mouse_delta = True

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.WINDOWFOCUSLOST:
            self._focused = False
            self._set_capture(False)
        elif event.type == pygame.WINDOWFOCUSGAINED:
            self._focused = True
        elif event.type == pygame.KEYDOWN and event.key == self._bindings.release_mouse:
            self._set_capture(False)
        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == self._bindings.capture_mouse_button
            and self._focused
            and not self._captured
        ):
            self._set_capture(True)

    def read(self) -> tuple[float, float, tuple[int, int]]:
        mouse_delta = pygame.mouse.get_rel()
        if not self._focused or not self._captured:
            return 0.0, 0.0, (0, 0)
        if self._discard_mouse_delta:
            mouse_delta = (0, 0)
            self._discard_mouse_delta = False

        keys = pygame.key.get_pressed()
        forward = int(keys[self._bindings.forward]) - int(keys[self._bindings.backward])
        right = int(keys[self._bindings.right]) - int(keys[self._bindings.left])
        return float(forward), float(right), mouse_delta

    def release(self):
        self._set_capture(False)
