import pygame

from engine.rendering.hud import TextOverlay
from engine.rendering.presentation import integer_viewport
from engine.scene.session import Dialog


def button_rects(render_size: tuple[int, int], count: int) -> tuple[pygame.Rect, ...]:
    width = min(280, render_size[0] - 32)
    left, top = (render_size[0] - width) // 2, int(render_size[1] * 0.58)
    return tuple(pygame.Rect(left, top + i * 42, width, 32)
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
    """Тихий экран поверх замершей сцены: заголовок и два пункта меню."""

    def __init__(self, context, style):
        super().__init__(context, style)
        self._title_font = pygame.font.Font(str(style.font_path) if style.font_path else None, style.font_size + 10)
        self._dialog_key = None

    def draw(self, dialog: Dialog, render_size: tuple[int, int], window_size: tuple[int, int]):
        hovered = dialog_action_at(dialog, pygame.mouse.get_pos(), window_size, render_size)
        key = (dialog, render_size, hovered)
        if key != self._dialog_key:
            surface = pygame.Surface(render_size, pygame.SRCALPHA)
            surface.fill((0, 0, 0, 235))
            title = self._title_font.render(dialog.title, self._style.antialias, (218, 216, 208))
            surface.blit(title, title.get_rect(center=(render_size[0] // 2, int(render_size[1] * 0.38))))
            if dialog.message:
                message = self._font.render(dialog.message, self._style.antialias, (153, 151, 145))
                surface.blit(message, message.get_rect(center=(render_size[0] // 2, int(render_size[1] * 0.47))))
            for button, rect in zip(dialog.buttons, button_rects(render_size, len(dialog.buttons))):
                color = (238, 236, 228) if hovered == button.action else (158, 156, 149)
                label = self._font.render(button.label, self._style.antialias, color)
                surface.blit(label, label.get_rect(center=rect.center))
            self._upload_surface(surface)
            self._dialog_key = key
        self._draw_texture(render_size, "center")
