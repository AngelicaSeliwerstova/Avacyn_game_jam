import pygame


class Window:
    """Создаёт окно и показывает готовый кадр."""

    def __init__(self, size: tuple[int, int], title: str):
        self.surface = pygame.display.set_mode(size)
        pygame.display.set_caption(title)

    def present(self):
        pygame.display.flip()
