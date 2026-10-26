import pygame

from engine.controllers.first_person import FirstPersonController
from engine.core.window import Window
from engine.input.bindings import InputBindings
from engine.input.keyboard_mouse import KeyboardMouse
from engine.rendering.renderer import Renderer
from engine.scene.camera import Camera
from engine.scene.level import Level


class Application:
    """Соединяет системы движка и выполняет основной цикл."""

    def __init__(
        self,
        window_size: tuple[int, int],
        window_title: str,
        fps_limit: int,
        background_color: tuple[int, int, int],
        opengl_version: tuple[int, int],
        vsync: bool,
        camera: Camera,
        controller: FirstPersonController,
        input_bindings: InputBindings,
        level: Level,
    ):
        self._window_size = window_size
        self._window_title = window_title
        self._fps_limit = fps_limit
        self._background_color = background_color
        self._opengl_version = opengl_version
        self._vsync = vsync
        self._camera = camera
        self._controller = controller
        self._input_bindings = input_bindings
        self._level = level
        self._running = False

    def run(self):
        pygame.init()
        renderer = None
        input_device = None

        try:
            window = Window(
                size=self._window_size,
                title=self._window_title,
                opengl_version=self._opengl_version,
                vsync=self._vsync,
            )
            renderer = Renderer(
                viewport_size=window.size,
                background_color=self._background_color,
                opengl_version=self._opengl_version,
                camera=self._camera,
                level=self._level,
            )
            clock = pygame.time.Clock()
            input_device = KeyboardMouse(self._input_bindings)
            self._running = True

            while self._running:
                # Clock возвращает миллисекунды, контроллер работает с секундами.
                delta_time = clock.tick(self._fps_limit) / 1000.0
                self._handle_events(input_device)
                if not self._running:
                    break

                forward, right, mouse_delta = input_device.read()
                self._controller.update(delta_time, forward, right, mouse_delta)
                renderer.render()
                window.present()
        finally:
            self._running = False
            # GPU-ресурсы освобождаем, пока OpenGL-окно ещё существует.
            try:
                try:
                    if input_device is not None:
                        input_device.release()
                finally:
                    if renderer is not None:
                        renderer.release()
            finally:
                pygame.quit()

    def _handle_events(self, input_device: KeyboardMouse):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
            input_device.handle_event(event)
