"""Recorder UI composited through the existing OpenGL text surface."""
import pygame
from engine.rendering.hud import TextOverlay
from engine.rendering.presentation import fit_viewport


def archive_layout(view, size):
    width, height = size
    gap, margin = 12, 16
    cw, ch = (width - 44) // 2, (height - 206) // 2
    cards = tuple(pygame.Rect(margin + i % 2 * (cw + gap), 76 + i // 2 * (ch + gap), cw, ch) for i in range(4))
    labels = [("archive_close", "Закрыть · Esc")]
    if not view.playing:
        labels.insert(0, ("archive_play" if view.solved else "archive_check", "Смотреть запись" if view.solved else "Восстановить запись"))
        if not view.solved:
            labels.insert(1, ("archive_reset", "Сбросить"))
            if view.hint_available:
                labels.insert(2, ("archive_hint", "Подсказка"))
    bw = (width - margin * 2 - gap * (len(labels) - 1)) // len(labels)
    buttons = tuple((action, label, pygame.Rect(margin + i * (bw + gap), height - 42, bw, 28))
                    for i, (action, label) in enumerate(labels))
    return cards, buttons


def archive_action_at(view, position, window_size, render_size):
    x, y, width, height = fit_viewport(window_size, render_size)
    top = window_size[1] - y - height
    if not width or not (x <= position[0] < x + width and top <= position[1] < top + height):
        return None
    point = ((position[0] - x) * render_size[0] / width, (position[1] - top) * render_size[1] / height)
    cards, buttons = archive_layout(view, render_size)
    for action, _, rect in buttons:
        if rect.collidepoint(point):
            return action
    if not view.solved and not view.playing:
        return next((f"archive_frame:{i}" for i, rect in enumerate(cards) if rect.collidepoint(point)), None)
    return None


class CCTVOverlay(TextOverlay):
    def __init__(self, context, style):
        super().__init__(context, style)
        font = str(style.font_path) if style.font_path else None
        self._small = pygame.font.Font(font, 13)
        self._caption_font = pygame.font.Font(font, 18)
        self._images, self._key = {}, None

    def _label(self, surface, text, pos, color=(194, 215, 196), font=None):
        surface.blit((font or self._small).render(text, True, color), pos)

    def _fit(self, surface, frame, rect):
        if frame.image not in self._images:
            self._images[frame.image] = pygame.image.load(frame.image)
        image = self._images[frame.image]
        factor = min(rect.width / image.get_width(), rect.height / image.get_height())
        scaled = pygame.transform.scale(image, (round(image.get_width() * factor), round(image.get_height() * factor)))
        surface.blit(scaled, scaled.get_rect(center=rect.center))

    def surface(self, view, size, hovered=None):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill((7, 13, 13, 255))
        width, height = size
        self._label(surface, "SECURITY ARCHIVE / CAM 03", (16, 12), font=self._font)
        pygame.draw.circle(surface, (185, 63, 49), (width - 70, 21), 4)
        self._label(surface, "REC", (width - 58, 14), (184, 107, 96))
        cards, buttons = archive_layout(view, size)
        if view.playing:
            frame = view.frames[view.frame_index]
            self._fit(surface, frame, pygame.Rect(16, 46, width - 32, height - 102))
            self._label(surface, frame.time, (28, 54), font=self._font)
            if view.interference:
                for y in range(48, height - 60, 4):
                    pygame.draw.line(surface, (64, 83, 71, 220), (16, y), (width - 16, y), 2)
                self._label(surface, "ПОТЕРЯ СИГНАЛА", (width // 2 - 80, height // 2), font=self._font)
            if view.caption:
                panel = pygame.Rect(26, height - 155, width - 52, 96)
                pygame.draw.rect(surface, (8, 14, 14, 246), panel)
                self._label(surface, view.speaker, (panel.x + 10, panel.y + 8), font=self._caption_font)
                for i, line in enumerate(self._wrap_line(view.caption, panel.width - 20, self._caption_font)):
                    self._label(surface, line, (panel.x + 10, panel.y + 32 + i * 22), (234, 233, 213), self._caption_font)
        else:
            self._label(surface, view.title, (16, 40), font=self._font)
            self._label(surface, view.instruction, (16, 62))
            for i, (frame, rect) in enumerate(zip(view.frames, cards)):
                active = view.selected == i
                pygame.draw.rect(surface, (19, 31, 28), rect)
                self._fit(surface, frame, pygame.Rect(rect.x + 4, rect.y + 4, rect.width - 8, rect.height - 32))
                pygame.draw.rect(surface, (215, 187, 105) if active else (62, 87, 75), rect, 2 if active else 1)
                self._label(surface, f"{i + 1:02} / {frame.time}", (rect.x + 8, rect.y + 7), (226, 231, 208))
                for j, line in enumerate(self._wrap_line(frame.title, rect.width - 12, self._small)[:2]):
                    self._label(surface, line, (rect.x + 6, rect.bottom - 29 + j * 13))
            text = view.frames[view.selected].description if view.selected is not None else view.message
            for i, line in enumerate(self._wrap_line(text, width - 32, self._small)[:3]):
                self._label(surface, line, (16, height - 94 + i * 15), (222, 199, 143))
        for action, label, rect in buttons:
            pygame.draw.rect(surface, (66, 87, 71) if hovered == action else (32, 51, 44), rect, border_radius=3)
            lines = self._wrap_line(label, rect.width - 8, self._small)
            for i, text in enumerate(lines[:2]):
                rendered = self._small.render(text, True, (229, 233, 215))
                surface.blit(rendered, rendered.get_rect(center=(rect.centerx, rect.centery + (i - (len(lines) - 1) / 2) * 13)))
        return surface

    def draw(self, view, render_size, window_size):
        hovered = archive_action_at(view, pygame.mouse.get_pos(), window_size, render_size)
        key = view, render_size, hovered
        if self._key != key:
            self._upload_surface(self.surface(view, render_size, hovered))
            self._key = key
        self._draw_texture(render_size, "center")
