import pygame

from engine.rendering.hud import TextOverlay
from engine.rendering.presentation import fit_viewport
from engine.scene.session import Dialog


def button_rects(render_size: tuple[int, int], count: int) -> tuple[pygame.Rect, ...]:
    width = min(280, render_size[0] - 32)
    left, top = (render_size[0] - width) // 2, int(render_size[1] * 0.58)
    return tuple(pygame.Rect(left, top + i * 42, width, 32)
                 for i in range(count))


def conversation_rects(render_size, count):
    margin = 16
    panel = pygame.Rect(margin, render_size[1] - 112 - count * 48,
                        render_size[0] - margin * 2, 96 + count * 48)
    buttons = tuple(pygame.Rect(panel.left + 12, panel.top + 98 + i * 48,
                               panel.width - 24, 42) for i in range(count))
    return panel, buttons


def dialog_button_rects(dialog, render_size):
    return (conversation_rects(render_size, len(dialog.buttons))[1]
            if dialog.presentation == "conversation" else button_rects(render_size, len(dialog.buttons)))


def dialog_action_at(dialog: Dialog, position, window_size, render_size) -> str | None:
    x, y, width, height = fit_viewport(window_size, render_size)
    # Pygame считает Y сверху, а viewport OpenGL - снизу.
    top = window_size[1] - y - height
    if not width or not (x <= position[0] < x + width and top <= position[1] < top + height):
        return None
    point = ((position[0] - x) * render_size[0] / width,
             (position[1] - top) * render_size[1] / height)
    return next((button.action for button, rect in zip(dialog.buttons, dialog_button_rects(dialog, render_size))
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
            if dialog.presentation == "conversation":
                self._draw_conversation(surface, dialog, render_size, hovered)
                self._upload_surface(surface)
                self._dialog_key = key
                self._draw_texture(render_size, "center")
                return
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

    def _draw_conversation(self, surface, dialog, render_size, hovered):
        # Outside this bottom panel the alpha stays zero: the scene remains visible.
        panel, buttons = conversation_rects(render_size, len(dialog.buttons))
        pygame.draw.rect(surface, (12, 18, 19, 232), panel, border_radius=8)
        pygame.draw.line(surface, (143, 174, 155), panel.topleft, panel.topright, 2)
        title = self._font.render(dialog.title, self._style.antialias, (181, 207, 186))
        surface.blit(title, (panel.left + 14, panel.top + 8))
        message_lines = self._wrap_line(dialog.message, panel.width - 28, self._font)
        line_height = self._font.get_linesize()
        for index, line in enumerate(message_lines[:3]):
            text = self._font.render(line, self._style.antialias, (245, 243, 230))
            surface.blit(text, (panel.left + 14, panel.top + 31 + index * line_height))
        for button, rect in zip(dialog.buttons, buttons):
            active = hovered == button.action
            pygame.draw.rect(surface, (58, 80, 70) if active else (31, 43, 42), rect, border_radius=4)
            pygame.draw.rect(surface, (157, 192, 163) if active else (70, 88, 79), rect, 1, border_radius=4)
            lines = self._wrap_line(button.label, rect.width - 20, self._font)
            for index, line in enumerate(lines[:2]):
                label = self._font.render(line, self._style.antialias, (246, 243, 228))
                y = rect.centery - len(lines[:2]) * line_height // 2 + index * line_height
                surface.blit(label, (rect.left + 10, y))
