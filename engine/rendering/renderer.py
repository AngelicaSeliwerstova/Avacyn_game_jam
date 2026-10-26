import pygame


class Renderer:
    """Рисует содержимое кадра. Пока только очищает его цветом фона."""

    def __init__(
        self,
        surface: pygame.Surface,
        background_color: tuple[int, int, int],
    ):
        self._surface = surface
        self._background_color = background_color

    def render(self):
        self._surface.fill(self._background_color)
