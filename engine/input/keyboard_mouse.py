import pygame

from engine.input.bindings import InputBindings
from engine.input.state import InputState


class KeyboardMouse:
    """Читает ввод и освобождает мышь при потере фокуса или по Esc."""

    def __init__(self, bindings: InputBindings):
        self._bindings = bindings
        self._focused = bool(pygame.key.get_focused())
        self._captured = False
        self._discard_mouse_delta = True
        self._jump_queued = False
        self._jump_held = False
        self._interact_queued = False
        self._interact_held = False
        self._flashlight_queued = False
        self._flashlight_held = False
        self._camera_editor_queued = False
        self._camera_add_queued = False
        self._camera_delete_queued = False
        self._object_add_queued = False
        self._creator_material_queued = False
        self._set_capture(self._focused)

    def _set_capture(self, captured: bool):
        pygame.event.set_grab(captured)
        pygame.mouse.set_visible(not captured)
        pygame.mouse.get_rel()
        self._captured = captured
        self._jump_queued = False
        self._jump_held = bool(
            captured and self._bindings.jump is not None
            and pygame.key.get_pressed()[self._bindings.jump]
        )
        self._interact_queued = False
        self._interact_held = bool(
            captured and self._bindings.interact is not None
            and pygame.key.get_pressed()[self._bindings.interact]
        )
        self._flashlight_queued = False
        self._flashlight_held = bool(
            captured and self._bindings.toggle_flashlight is not None
            and pygame.key.get_pressed()[self._bindings.toggle_flashlight]
        )
        self._camera_editor_queued = False
        self._camera_add_queued = False
        self._camera_delete_queued = False
        self._object_add_queued = False
        self._creator_material_queued = False
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
        elif event.type == pygame.KEYUP and event.key == self._bindings.toggle_flashlight:
            self._flashlight_held = False
        elif event.type == pygame.KEYDOWN and event.key == self._bindings.toggle_flashlight:
            if (self._focused and self._captured and not self._flashlight_held
                    and not getattr(event, "repeat", False)):
                self._flashlight_queued = not self._flashlight_queued
            self._flashlight_held = True
        elif event.type == pygame.KEYUP and event.key == self._bindings.interact:
            self._interact_held = False
        elif event.type == pygame.KEYDOWN and event.key == self._bindings.interact:
            if (self._focused and self._captured and not self._interact_held
                    and not getattr(event, "repeat", False)):
                self._interact_queued = True
            self._interact_held = True
        elif event.type == pygame.KEYUP and event.key == self._bindings.jump:
            self._jump_held = False
        elif event.type == pygame.KEYDOWN and event.key == self._bindings.jump:
            if (self._focused and self._captured and not self._jump_held
                    and not getattr(event, "repeat", False)):
                self._jump_queued = True
            self._jump_held = True
        elif event.type == pygame.KEYDOWN and not getattr(event, "repeat", False):
            if self._focused and self._captured:
                if event.key == self._bindings.toggle_camera_editor:
                    self._camera_editor_queued = True
                elif event.key == self._bindings.add_camera:
                    self._camera_add_queued = True
                elif event.key == self._bindings.delete_camera:
                    self._camera_delete_queued = True
                elif event.key == self._bindings.add_object:
                    self._object_add_queued = True
                elif event.key == self._bindings.cycle_creator_material:
                    self._creator_material_queued = True
        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == self._bindings.capture_mouse_button
            and self._focused
            and not self._captured
        ):
            self._set_capture(True)

    def read(self) -> InputState:
        mouse_delta = pygame.mouse.get_rel()
        if not self._focused or not self._captured:
            return InputState()
        if self._discard_mouse_delta:
            mouse_delta = (0, 0)
            self._discard_mouse_delta = False

        keys = pygame.key.get_pressed()
        forward = int(keys[self._bindings.forward]) - int(keys[self._bindings.backward])
        right = int(keys[self._bindings.right]) - int(keys[self._bindings.left])
        state = InputState(
            forward=float(forward), right=float(right), mouse_delta=mouse_delta,
            sprint=any(keys[key] for key in self._bindings.sprint_keys),
            jump=self._jump_queued,
            crouch=any(keys[key] for key in self._bindings.crouch_keys),
            interact=self._interact_queued,
            zoom=(self._bindings.zoom_mouse_button is not None
                  and pygame.mouse.get_pressed(5)[self._bindings.zoom_mouse_button - 1]),
            toggle_flashlight=self._flashlight_queued,
            look_back=(self._bindings.look_back is not None
                       and bool(keys[self._bindings.look_back])),
            toggle_camera_editor=self._camera_editor_queued,
            add_camera=self._camera_add_queued,
            delete_camera=self._camera_delete_queued,
            add_object=self._object_add_queued,
            cycle_creator_material=self._creator_material_queued,
            creator_up=(self._bindings.creator_up is not None
                        and bool(keys[self._bindings.creator_up])),
        )
        self._jump_queued = False
        self._interact_queued = False
        self._flashlight_queued = False
        self._camera_editor_queued = False
        self._camera_add_queued = False
        self._camera_delete_queued = False
        self._object_add_queued = False
        self._creator_material_queued = False
        return state

    @property
    def status_text(self) -> str:
        if not self._focused:
            return "UNFOCUSED"
        return "CAPTURED" if self._captured else "CURSOR FREE"

    def release(self):
        self._set_capture(False)
