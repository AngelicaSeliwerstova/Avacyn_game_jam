import pygame

from engine.rendering.hud import TextOverlay
from engine.rendering.presentation import integer_viewport
from engine.scene.session import Dialog


def button_rects(render_size: tuple[int, int], count: int) -> tuple[pygame.Rect, ...]:
    width = min(360, render_size[0] - 32)
    left, top = (render_size[0] - width) // 2, (render_size[1] - 210) // 2
    gap, padding = 12, 18
    button_width = (width - 2 * padding - gap * (count - 1)) // count
    return tuple(pygame.Rect(left + padding + i * (button_width + gap), top + 145, button_width, 42)
                 for i in range(count))


def dialog_action_at(dialog: Dialog, position, window_size, render_size) -> str | None:
    x, y, width, height = integer_viewport(window_size, render_size)
    # Pygame считает Y сверху, а viewport OpenGL - снизу.
    top = window_size[1] - y - height
    if not width or not (x <= position[0] < x + width and top <= position[1] < top + height):
        return None
    point = ((position[0] - x) * render_size[0] / width,
             (position[1] - top) * render_size[1] / height)
    return next((button.action for button, rect in zip(dialog.buttons, button_rects(render_size, len(dialog.buttons)))
                 if rect.collidepoint(point)), None)


class DialogOverlay(TextOverlay):
    """Затемнение сцены и диалог с кнопками поверх готового кадра."""

    def __init__(self, context, style):
        super().__init__(context, style)
        heading_path = style.heading_font_path or style.font_path
        self._title_font = pygame.font.Font(str(heading_path) if heading_path else None, style.font_size + 12)
        self._dialog_key = None

    def draw(self, dialog: Dialog, render_size: tuple[int, int]):
        key = (dialog, render_size)
        if key != self._dialog_key:
            surface = pygame.Surface(render_size, pygame.SRCALPHA)
            surface.fill((3, 6, 12, 185))
            panel = pygame.Rect(0, 0, min(360, render_size[0] - 32), 210)
            panel.center = (render_size[0] // 2, render_size[1] // 2)
            pygame.draw.rect(surface, (14, 20, 29, 255), panel)
            pygame.draw.rect(surface, (74, 91, 110, 255), panel, 1)
            pygame.draw.rect(surface, (150, 50, 55, 255), (panel.x, panel.y, panel.width, 3))
            title = self._title_font.render(dialog.title, self._style.antialias, (236, 192, 190))
            message = self._font.render(dialog.message, self._style.antialias, (207, 216, 226))
            surface.blit(title, title.get_rect(center=(panel.centerx, panel.top + 46)))
            surface.blit(message, message.get_rect(center=(panel.centerx, panel.top + 91)))
            for button, rect in zip(dialog.buttons, button_rects(render_size, len(dialog.buttons))):
                pygame.draw.rect(surface, (32, 46, 63, 255), rect)
                pygame.draw.rect(surface, (107, 130, 153, 255), rect, 1)
                label = self._font.render(button.label, self._style.antialias, (232, 235, 239))
                surface.blit(label, label.get_rect(center=rect.center))
            self._upload_surface(surface)
            self._dialog_key = key
        self._draw_texture(render_size, "center")
