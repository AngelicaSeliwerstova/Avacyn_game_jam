import pygame

from engine.core.window import Window
from engine.rendering.renderer import Renderer


class Application:
    """Соединяет системы движка и выполняет основной цикл."""

    def __init__(
        self,
        window_size: tuple[int, int],
        window_title: str,
        fps_limit: int,
        background_color: tuple[int, int, int],
    ):
        self._window_size = window_size
        self._window_title = window_title
        self._fps_limit = fps_limit
        self._background_color = background_color
        self._running = False

    def run(self):
        pygame.init()

        try:
            window = Window(size=self._window_size, title=self._window_title)
            renderer = Renderer(
                surface=window.surface,
                background_color=self._background_color,
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
            pygame.quit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._running = False
