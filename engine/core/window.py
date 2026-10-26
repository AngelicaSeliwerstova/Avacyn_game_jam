import pygame


class Window:
    """Создаёт окно и показывает готовый кадр."""

    def __init__(
        self,
        size: tuple[int, int],
        title: str,
        opengl_version: tuple[int, int],
        vsync: bool,
    ):
        major, minor = opengl_version
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, major)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, minor)
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE
        )
        # Сглаживание MSAA отключено для будущего PSX-профиля.
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 0)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 0)
        pygame.display.set_mode(
            size,
            flags=pygame.OPENGL | pygame.DOUBLEBUF,
            vsync=int(vsync),
        )
        pygame.display.set_caption(title)

    @property
    def size(self) -> tuple[int, int]:
        return pygame.display.get_window_size()

    def present(self):
        pygame.display.flip()
