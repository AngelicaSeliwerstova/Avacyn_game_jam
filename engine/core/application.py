import pygame

from engine.core.window import Window
from engine.input.bindings import InputBindings
from engine.input.keyboard_mouse import KeyboardMouse
from engine.particles.snow import Snowfall
from engine.rendering.renderer import Renderer
from engine.rendering.texture import TextureSettings
from engine.scene.entity import ControlledEntity
from engine.scene.level import Level


class Application:
    """Соединяет системы движка и выполняет основной цикл."""

    def __init__(
        self,
        window_size: tuple[int, int],
        render_size: tuple[int, int],
        window_title: str,
        fps_limit: int,
        background_color: tuple[int, int, int],
        opengl_version: tuple[int, int],
        vsync: bool,
        controlled_entity: ControlledEntity,
        input_bindings: InputBindings,
        level: Level,
        snow: Snowfall | None = None,
        textures: TextureSettings | None = None,
    ):
        self._window_size = window_size
        self._render_size = render_size
        self._window_title = window_title
        self._fps_limit = fps_limit
        self._background_color = background_color
        self._opengl_version = opengl_version
        self._vsync = vsync
        self._controlled_entity = controlled_entity
        self._input_bindings = input_bindings
        self._level = level
        self._snow = snow
        self._textures = textures
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
                minimum_size=self._render_size,
            )
            renderer = Renderer(
                render_size=self._render_size,
                background_color=self._background_color,
                opengl_version=self._opengl_version,
                camera=self._controlled_entity.camera,
                level=self._level,
                snow=self._snow,
                textures=self._textures,
            )
            clock = pygame.time.Clock()
            input_device = KeyboardMouse(self._input_bindings)
            self._running = True

            while self._running:
                # Clock возвращает миллисекунды, контроллер работает с секундами.
                delta_time = clock.tick(self._fps_limit) / 1000.0
                self._handle_events(input_device, window)
                if not self._running:
                    break

                inputs = input_device.read()
                self._controlled_entity.update(delta_time, inputs)
                if self._snow is not None:
                    self._snow.update(delta_time)
                renderer.render(window.size)
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

    def _handle_events(self, input_device: KeyboardMouse, window: Window):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
            elif event.type == pygame.KEYDOWN and event.key == self._input_bindings.toggle_fullscreen:
                input_device.release()
                window.toggle_fullscreen()
            window.handle_event(event)
            input_device.handle_event(event)
