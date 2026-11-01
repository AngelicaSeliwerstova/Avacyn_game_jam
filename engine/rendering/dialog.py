import pygame
import math
from pathlib import Path

from engine.rendering.hud import TextOverlay
from engine.rendering.presentation import fit_viewport
from engine.scene.session import Dialog


def button_rects(render_size: tuple[int, int], count: int) -> tuple[pygame.Rect, ...]:
    width = min(280, render_size[0] - 32)
    left, top = (render_size[0] - width) // 2, int(render_size[1] * 0.58)
    return tuple(pygame.Rect(left, top + i * 42, width, 32)
                 for i in range(count))


def conversation_rects(render_size, count, *, content_height=124):
    margin = 16
    button_height = max(0, count * 60 - 6)
    height = content_height + button_height + 12
    panel = pygame.Rect(margin, render_size[1] - margin - height,
                        render_size[0] - margin * 2, height)
    # Anchor actions to the bottom so their hit boxes do not depend on text length.
    button_top = panel.bottom - 12 - button_height
    buttons = tuple(pygame.Rect(panel.left + 12, button_top + i * 60,
                               panel.width - 24, 54) for i in range(count))
    return panel, buttons


def dialog_button_rects(dialog, render_size):
    if dialog.presentation == "menu":
        width, height = render_size
        return tuple(pygame.Rect(44, int(height * .48) + i * 44, min(282, width - 88), 36)
                     for i in range(len(dialog.buttons)))
    if dialog.presentation == "filing_archive":
        width, height = render_size
        if dialog.filing_year is None:
            cards = tuple(pygame.Rect(28 + i % 3 * ((width - 56) // 3), 154 + i // 3 * 60,
                                      (width - 74) // 3, 48) for i in range(len(dialog.buttons) - 1))
            return cards + (pygame.Rect(28, height - 52, width - 56, 34),)
        count = len(dialog.buttons)
        return tuple(pygame.Rect(36, height - 52 - (count - 1 - i) * 44, width - 72, 36)
                     for i in range(count))
    if dialog.presentation in ("document", "plan"):
        count = len(dialog.buttons)
        width = (render_size[0] - 96) // max(1, count)
        return tuple(pygame.Rect(44 + i * width, render_size[1] - 62, width - 8, 34)
                     for i in range(count))
    return (conversation_rects(render_size, len(dialog.buttons))[1]
            if dialog.presentation in ("conversation", "memory", "voiceover") else button_rects(render_size, len(dialog.buttons)))


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
            if dialog.presentation == "menu":
                self._draw_menu(surface, dialog, render_size, hovered)
            elif dialog.presentation in ("title", "interference", "blackout", "distortion", "whiteout"):
                self._draw_timed(surface, dialog, render_size)
            elif dialog.presentation in ("document", "plan"):
                self._draw_document(surface, dialog, render_size, hovered)
            elif dialog.presentation == "filing_archive":
                self._draw_filing_archive(surface, dialog, render_size, hovered)
            elif dialog.presentation in ("conversation", "memory", "voiceover"):
                if dialog.presentation == "memory":
                    surface.fill((25, 15, 8, 155))
                elif dialog.presentation == "voiceover":
                    surface.fill((22, 25, 18, 28))
                self._draw_conversation(surface, dialog, render_size, hovered)
            else:
                self._draw_modal(surface, dialog, render_size, hovered)
            self._upload_surface(surface)
            self._dialog_key = key
        self._draw_texture(render_size, "center")

    def _draw_menu(self, surface, dialog, size, hovered):
        if getattr(self, "_menu_background_size", None) != size:
            backdrop = pygame.Surface(size)
            backdrop.fill((8, 7, 14))
            path = Path(__file__).resolve().parents[2] / "resources/ui/menu_background.png"
            try:
                image = pygame.image.load(str(path))
                image = pygame.transform.smoothscale(image, size)
                backdrop.blit(image, (0, 0))
            except (OSError, pygame.error):
                pass
            shade = pygame.Surface(size, pygame.SRCALPHA)
            for x in range(size[0]):
                alpha = round(248 * max(0, 1 - x / (size[0] * .79)) ** 1.1)
                pygame.draw.line(shade, (8, 7, 15, alpha), (x, 0), (x, size[1]))
            backdrop.blit(shade, (0, 0))
            self._menu_background, self._menu_background_size = backdrop, size
        surface.blit(self._menu_background, (0, 0))
        pygame.draw.line(surface, (170, 128, 151), (44, 62), (82, 62), 2)
        if dialog.title == "АВАЦИН":
            font = pygame.font.Font(str(self._style.heading_font_path or self._style.font_path), 54)
        else:
            font = self._title_font
        title = font.render(dialog.title, True, (241, 231, 236))
        surface.blit(title, (44, 84))
        if dialog.message:
            y = 144
            for paragraph in dialog.message.split("\n"):
                for line in self._wrap_line(paragraph, min(285, size[0] - 88), self._font):
                    surface.blit(self._font.render(line, True, (187, 174, 192)), (44, y))
                    y += self._font.get_linesize()
        for button, rect in zip(dialog.buttons, dialog_button_rects(dialog, size)):
            selected = button.action == hovered or hovered is None and "return" in button.keys
            pygame.draw.rect(surface, (45, 31, 49) if selected else (11, 10, 19), rect, border_radius=2)
            pygame.draw.rect(surface, (179, 135, 163) if selected else (70, 57, 82), rect, 1, border_radius=2)
            if selected:
                pygame.draw.rect(surface, (208, 165, 187), (rect.x, rect.y, 3, rect.height))
            label = self._font.render(button.label, True, (247, 232, 241) if selected else (193, 181, 204))
            surface.blit(label, (rect.left + 16, rect.centery - label.get_height() // 2))

    def _draw_filing_archive(self, surface, dialog, size, hovered):
        surface.fill((13, 24, 24, 248))
        title = self._title_font.render(dialog.title, True, (229, 218, 181))
        surface.blit(title, (28, 22))
        pygame.draw.line(surface, (115, 135, 112), (28, 62), (size[0] - 28, 62))
        y = 76
        for paragraph in dialog.message.split("\n"):
            for line in self._wrap_line(paragraph, size[0] - 72, self._font):
                surface.blit(self._font.render(line, True, (211, 216, 198)), (36, y))
                y += self._font.get_linesize()
        for button, rect in zip(dialog.buttons, dialog_button_rects(dialog, size)):
            pygame.draw.rect(surface, (69, 88, 72) if hovered == button.action else (38, 54, 46), rect, border_radius=3)
            pygame.draw.rect(surface, (121, 129, 101), rect, 1, border_radius=3)
            if dialog.filing_year == 1981 and not dialog.filing_case and button.action == "files_case":
                pygame.draw.rect(surface, (154, 53, 43), (rect.x, rect.y, 8, rect.height))
            font = self._title_font if button.action.startswith("files_year:") else self._font
            text = font.render(button.label, True, (239, 230, 204))
            surface.blit(text, text.get_rect(center=rect.center))

    def _draw_modal(self, surface, dialog, render_size, hovered):
        surface.fill((0, 0, 0, 255 if dialog.presentation == "ending" else 235))
        title = self._title_font.render(dialog.title, self._style.antialias, (218, 216, 208))
        surface.blit(title, title.get_rect(center=(render_size[0] // 2, int(render_size[1] * 0.38))))
        if dialog.message:
            message = self._font.render(dialog.message, self._style.antialias, (153, 151, 145))
            surface.blit(message, message.get_rect(center=(render_size[0] // 2, int(render_size[1] * 0.47))))
        for button, rect in zip(dialog.buttons, button_rects(render_size, len(dialog.buttons))):
            color = (238, 236, 228) if hovered == button.action else (158, 156, 149)
            label = self._font.render(button.label, self._style.antialias, color)
            surface.blit(label, label.get_rect(center=rect.center))

    def _draw_timed(self, surface, dialog, render_size):
        surface.fill((0, 0, 0, round(255 * dialog.opacity)))
        if dialog.presentation == "whiteout":
            surface.fill((240, 238, 224, round(255 * dialog.opacity)))
        if dialog.presentation == "title":
            for text, font, y in ((dialog.title, self._title_font, 0.43),
                                  (dialog.message, self._font, 0.53)):
                label = font.render(text, True, (224, 225, 214))
                label.set_alpha(round(255 * dialog.opacity))
                surface.blit(label, label.get_rect(center=(render_size[0] // 2, int(render_size[1] * y))))
        elif dialog.presentation == "interference" and dialog.effect_time < 1.2:
            # The first second breaks the CCTV image; then hold complete black.
            surface.fill((0, 0, 0, round(80 + 175 * dialog.effect_time / 1.2)))
            frame = int(dialog.effect_time * 30)
            for y in range(0, render_size[1], 4):
                intensity = (y * 73 + frame * 97) % 170
                offset = int(math.sin(y + frame * 0.7) * 80)
                pygame.draw.line(surface, (intensity, intensity, intensity, 180),
                                 (max(0, offset), y), (render_size[0] + min(0, offset), y))
        elif dialog.presentation == "distortion":
            surface.fill((22, 29, 27, 25))
            for y in range(0, render_size[1], 6):
                offset = round(math.sin(y * 0.1 + dialog.effect_time * 18) * 12)
                pygame.draw.line(surface, (115, 139, 121, 36), (max(0, offset), y), (render_size[0], y))

    def _draw_document(self, surface, dialog, render_size, hovered):
        surface.fill((0, 0, 0, 210))
        panel = pygame.Rect(28, 16, render_size[0] - 56, render_size[1] - 32)
        pygame.draw.rect(surface, (224, 218, 197), panel, border_radius=3)
        title = self._title_font.render(dialog.title, True, (37, 52, 47))
        surface.blit(title, (panel.left + 18, panel.top + 14))
        pygame.draw.line(surface, (118, 130, 112), (panel.left + 18, 68), (panel.right - 18, 68))
        if dialog.presentation == "plan":
            self._draw_plan(surface, dialog, pygame.Rect(48, 96, render_size[0] - 96, render_size[1] - 178))
            label = self._font.render(dialog.message, True, (61, 73, 61))
            surface.blit(label, (48, 72))
        else:
            y = 94
            for paragraph in dialog.message.split("\n"):
                for line in self._wrap_line(paragraph, panel.width - 48, self._font):
                    if "█" in line:
                        prefix, redacted = line.split("█", 1)
                        label = self._font.render(prefix, True, (42, 44, 38))
                        surface.blit(label, (panel.left + 24, y))
                        width = self._font.size("М" * (1 + redacted.count("█")))[0]
                        pygame.draw.rect(surface, (30, 32, 28),
                                         (panel.left + 24 + label.get_width(), y + 4, width, self._font.get_height() - 6))
                    else:
                        label = self._font.render(line, True, (42, 44, 38))
                        surface.blit(label, (panel.left + 24, y))
                    y += self._font.get_linesize()
        for button, rect in zip(dialog.buttons, dialog_button_rects(dialog, render_size)):
            pygame.draw.rect(surface, (65, 91, 77) if hovered == button.action else (49, 68, 59), rect,
                             border_radius=3)
            label = self._font.render(button.label, True, (242, 238, 218))
            surface.blit(label, label.get_rect(center=rect.center))

    def _draw_plan(self, surface, dialog, area):
        if not dialog.plan_walls:
            return
        x1 = min(w[0] for w in dialog.plan_walls)
        z1 = min(w[1] for w in dialog.plan_walls)
        x2 = max(w[2] for w in dialog.plan_walls)
        z2 = max(w[3] for w in dialog.plan_walls)
        scale = min(area.width / (x2 - x1), area.height / (z2 - z1))
        left = area.centerx - (x2 - x1) * scale / 2
        top = area.centery - (z2 - z1) * scale / 2

        def point(x, z):
            return round(left + (x - x1) * scale), round(top + (z - z1) * scale)

        for a, b, c, d in dialog.plan_walls:
            start, end = point(a, b), point(c, d)
            pygame.draw.rect(surface, (73, 90, 76), (*start, max(2, end[0] - start[0]), max(2, end[1] - start[1])))
        if dialog.plan_stair is not None:
            x, z, radius = dialog.plan_stair
            pygame.draw.circle(surface, (100, 119, 96), point(x, z), max(3, round(radius * scale)), 1)
        for x, z, text in dialog.plan_labels:
            label = self._font.render(text, True, (151, 48, 37) if text in dialog.plan_highlights else (34, 52, 42))
            rect = label.get_rect(center=point(x, z))
            pygame.draw.rect(surface, (224, 218, 197), rect.inflate(3, 1))
            surface.blit(label, rect)
        if dialog.plan_player is not None:
            pygame.draw.circle(surface, (169, 49, 35), point(*dialog.plan_player), 4)

    def _draw_conversation(self, surface, dialog, render_size, hovered):
        # Outside this bottom panel the alpha stays zero: the scene remains visible.
        panel, buttons = conversation_rects(render_size, len(dialog.buttons))
        font = self._font
        # Measure the entire line before the typewriter reveal, keeping the panel steady.
        available_height = (buttons[0].top if buttons else panel.bottom - 12) - 16
        font_size = self._style.font_size
        while True:
            line_height = font.get_linesize()
            message_lines = [line for paragraph in dialog.message.split("\n")
                             for line in self._wrap_line(paragraph, panel.width - 28, font)]
            content_height = 8 + self._font.get_height() + 6 + max(3, len(message_lines)) * line_height + 12
            if content_height <= available_height or font_size <= 1:
                break
            font_size -= 1
            font = pygame.font.Font(str(self._style.font_path) if self._style.font_path else None, font_size)
        panel, buttons = conversation_rects(render_size, len(dialog.buttons), content_height=content_height)
        pygame.draw.rect(surface, (12, 18, 19, 232), panel, border_radius=8)
        pygame.draw.line(surface, (143, 174, 155), panel.topleft, panel.topright, 2)
        title = self._font.render(dialog.title, self._style.antialias, (181, 207, 186))
        surface.blit(title, (panel.left + 14, panel.top + 8))
        visible = dialog.message if dialog.visible_characters is None else dialog.message[:dialog.visible_characters]
        message_lines = [line for paragraph in visible.split("\n")
                         for line in self._wrap_line(paragraph, panel.width - 28, font)]
        message_top = panel.top + 8 + self._font.get_height() + 6
        for index, line in enumerate(message_lines):
            text = font.render(line, self._style.antialias, (245, 243, 230))
            surface.blit(text, (panel.left + 14, message_top + index * line_height))
        line_height = self._font.get_linesize()
        for button, rect in zip(dialog.buttons, buttons):
            active = hovered == button.action
            pygame.draw.rect(surface, (58, 80, 70) if active else (31, 43, 42), rect, border_radius=4)
            pygame.draw.rect(surface, (157, 192, 163) if active else (70, 88, 79), rect, 1, border_radius=4)
            lines = self._wrap_line(button.label, rect.width - 20, self._font)
            for index, line in enumerate(lines[:2]):
                label = self._font.render(line, self._style.antialias, (246, 243, 228))
                y = rect.centery - len(lines[:2]) * line_height // 2 + index * line_height
                surface.blit(label, (rect.left + 10, y))
