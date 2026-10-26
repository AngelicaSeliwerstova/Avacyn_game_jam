import pygame

from engine.core.window import Window
from engine.rendering.renderer import Renderer
from engine.scene.camera import Camera


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
    ):
        self._window_size = window_size
        self._window_title = window_title
        self._fps_limit = fps_limit
        self._background_color = background_color
        self._opengl_version = opengl_version
        self._vsync = vsync
        self._camera = camera
        self._running = False

    def run(self):
        pygame.init()
        renderer = None

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
            )
            clock = pygame.time.Clock()
            self._running = True

            while self._running:
                self._handle_events()
                if not self._running:
                    break

                # Здесь позже появится обновление игровой сцены.
                renderer.render()
                window.present()
                clock.tick(self._fps_limit)
        finally:
            self._running = False
            # GPU-ресурсы освобождаем, пока OpenGL-окно ещё существует.
            try:
                if renderer is not None:
                    renderer.release()
            finally:
                pygame.quit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._running = False
