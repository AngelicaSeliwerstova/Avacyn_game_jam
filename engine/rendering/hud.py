from dataclasses import dataclass
from pathlib import Path

import moderngl
import pygame

from engine.rendering.presentation import horizontal_side_bars, integer_viewport


@dataclass(frozen=True)
class HudStyle:
    font_size: int = 18
    margin: int = 8
    font_path: Path | None = None
    heading_font_path: Path | None = None
    antialias: bool = True
    line_gap: int = 2


class TextOverlay:
    """Небольшая подпись поверх внутреннего кадра; текстура меняется вместе с текстом."""

    def __init__(self, context: moderngl.Context, style: HudStyle):
        self._context = context
        self._style = style
        self._font = pygame.font.Font(str(style.font_path) if style.font_path is not None else None,
                                      style.font_size)
        self._heading_font = (pygame.font.Font(str(style.heading_font_path), style.font_size)
                              if style.heading_font_path is not None else self._font)
        self._text = None
        self._wrap_width = None
        self._fill_width = False
        self._texture = None
        self._program = None
        self._vertices = None
        try:
            shaders = Path(__file__).resolve().parent / "shaders"
            self._program = context.program(
                vertex_shader=(shaders / "present.vert").read_text(encoding="utf-8"),
                fragment_shader=(shaders / "present.frag").read_text(encoding="utf-8"),
            )
            self._program["scene_texture"].value = 0
            self._vertices = context.vertex_array(self._program, [])
        except Exception:
            self.release()
            raise

    def draw(self, text: str, render_size: tuple[int, int], *, anchor: str = "top_left",
             max_width: int | None = None, fill_width: bool = False,
             anchor_bounds: tuple[int, int, int, int] | None = None):
        if not text:
            return
        if text != self._text or max_width != self._wrap_width or fill_width != self._fill_width:
            lines = []
            for index, string in enumerate(text.splitlines()):
                font = self._heading_font if index == 0 else self._font
                strings = (self._wrap_line(string, max(1, max_width - 2 * self._style.margin), font)
                           if max_width is not None else [string])
                lines.extend(font.render(line, self._style.antialias, (230, 228, 212)) for line in strings)
            padding = self._style.margin
            width = max_width if fill_width and max_width is not None else (
                max(line.get_width() for line in lines) + 2 * padding
            )
            # Общий диапазон видимых глифов сохраняет базовую линию и убирает
            # лишние вертикальные поля TTF; хвосты букв и диакритика остаются целыми.
            bounds = [line.get_bounding_rect() for line in lines]
            ink = [rect for rect in bounds if rect.height]
            top = min((rect.top for rect in ink), default=0)
            bottom = max((rect.bottom for rect in ink), default=self._font.get_height())
            line_height = bottom - top + self._style.line_gap
            height = len(lines) * line_height - self._style.line_gap + 2 * padding
            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            surface.fill((10, 10, 14, 205))
            for index, line in enumerate(lines):
                surface.blit(line, (padding, padding + index * line_height - top))
            self._upload_surface(surface)
            self._text = text
            self._wrap_width = max_width
            self._fill_width = fill_width
        self._draw_texture(render_size, anchor, anchor_bounds)

    def _upload_surface(self, surface: pygame.Surface):
        if self._texture is not None:
            self._texture.release()
        self._texture = self._context.texture(
            surface.get_size(), 4, pygame.image.tobytes(surface, "RGBA", True), alignment=1,
        )
        self._texture.filter = moderngl.NEAREST, moderngl.NEAREST

    def _draw_texture(self, render_size: tuple[int, int], anchor: str,
                      anchor_bounds: tuple[int, int, int, int] | None = None):
        width, height = self._texture.size
        margin = self._style.margin
        x, y, bounds_width, bounds_height = (
            anchor_bounds if anchor_bounds is not None
            else (0, 0, render_size[0], render_size[1])
        )
        if anchor == "top_left":
            position = (x + margin, y + bounds_height - height - margin)
        elif anchor == "bottom_right":
            position = (x + bounds_width - width - margin, y + margin)
        elif anchor == "bottom_center":
            position = (x + (bounds_width - width) // 2, y + margin)
        elif anchor == "center":
            position = (x + (bounds_width - width) // 2, y + (bounds_height - height) // 2)
        elif anchor == "center_left":
            position = (x + margin, y + (bounds_height - height) // 2)
        elif anchor == "center_right":
            position = (x + bounds_width - width - margin, y + (bounds_height - height) // 2)
        elif anchor == "top_right":
            position = (x + bounds_width - width - margin, y + bounds_height - height - margin)
        else:
            raise ValueError(f"Unknown text anchor: {anchor}")
        self._context.viewport = (*position, width, height)
        self._context.disable(moderngl.DEPTH_TEST)
        self._context.enable(moderngl.BLEND)
        self._context.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        try:
            self._texture.use(location=0)
            self._vertices.render(mode=moderngl.TRIANGLES, vertices=3)
        finally:
            self._context.disable(moderngl.BLEND)

    def _wrap_line(self, text: str, width: int, font: pygame.font.Font) -> list[str]:
        lines, current = [], ""
        for word in text.split():
            candidate = f"{current} {word}" if current else word
            if current and font.size(candidate)[0] > width:
                lines.append(current)
                current = ""
            # Длинное слово тоже не должно выходить за границы кадра.
            for character in (" " if current else "") + word:
                if current and font.size(current + character)[0] > width:
                    lines.append(current)
                    current = ""
                current += character
        return lines + [current]

    def release(self):
        for name in ("_texture", "_vertices", "_program"):
            resource = getattr(self, name)
            if resource is not None:
                resource.release()
                setattr(self, name, None)


class AimOverlay:
    """Точка точно в центре кадра и подсказка действия снизу."""

    def __init__(self, context: moderngl.Context, style: HudStyle):
        self._context = context
        self._style = style
        self._text = self._texture = self._program = self._vertices = None
        try:
            self._text = TextOverlay(context, style)
            shaders = Path(__file__).resolve().parent / "shaders"
            self._program = context.program(
                vertex_shader=(shaders / "present.vert").read_text(encoding="utf-8"),
                fragment_shader=(shaders / "present.frag").read_text(encoding="utf-8"),
            )
            self._program["scene_texture"].value = 0
            self._vertices = context.vertex_array(self._program, [])
            pixels = bytes(channel for y in range(4) for x in range(4)
                           for channel in ((230, 228, 212, 255) if 1 <= x <= 2 and 1 <= y <= 2
                                           else (0, 0, 0, 180)))
            self._texture = context.texture((4, 4), 4, pixels)
            self._texture.filter = moderngl.NEAREST, moderngl.NEAREST
        except Exception:
            self.release()
            raise

    def draw(self, text: str, render_size: tuple[int, int]):
        self._text.draw(text, render_size, anchor="bottom_center",
                        max_width=render_size[0] - 2 * self._style.margin)
        self._context.viewport = (render_size[0] // 2 - 2, render_size[1] // 2 - 2, 4, 4)
        self._context.disable(moderngl.DEPTH_TEST)
        self._context.enable(moderngl.BLEND)
        self._context.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        try:
            self._texture.use(location=0)
            self._vertices.render(mode=moderngl.TRIANGLES, vertices=3)
        finally:
            self._context.disable(moderngl.BLEND)

    def release(self):
        for name in ("_text", "_texture", "_vertices", "_program"):
            resource = getattr(self, name)
            if resource is not None:
                resource.release()
                setattr(self, name, None)


class CreatorSidebarOverlay:
    """Draws compact creator controls in the unused side bars around the game view."""

    MINIMUM_BAR_WIDTH = 180

    def __init__(self, context: moderngl.Context, style: HudStyle):
        sidebar_style = HudStyle(
            font_size=max(12, style.font_size - 4),
            margin=max(8, style.margin),
            font_path=style.font_path,
            heading_font_path=style.heading_font_path,
            antialias=style.antialias,
            line_gap=style.line_gap,
        )
        self._margin = sidebar_style.margin
        self._left = TextOverlay(context, sidebar_style)
        self._right = TextOverlay(context, sidebar_style)

    def draw(self, window_size: tuple[int, int], render_size: tuple[int, int],
             text: tuple[str, str]):
        left_width, right_width = horizontal_side_bars(window_size, render_size)
        margin = self._margin
        if left_width >= self.MINIMUM_BAR_WIDTH:
            self._left.draw(
                text[0], window_size, anchor="center_left",
                max_width=left_width - margin * 2, fill_width=True,
            )
        if right_width >= self.MINIMUM_BAR_WIDTH:
            self._right.draw(
                text[1], window_size, anchor="center_right",
                max_width=right_width - margin * 2, fill_width=True,
            )
        if left_width < self.MINIMUM_BAR_WIDTH and right_width < self.MINIMUM_BAR_WIDTH:
            panel_width = min(180, max(1, (render_size[0] - margin * 3) // 2))
            viewport_x, viewport_y, viewport_width, viewport_height = integer_viewport(
                window_size, render_size,
            )
            viewport = (viewport_x, viewport_y, viewport_width, viewport_height)
            self._left.draw(
                text[0], window_size, anchor="center_left",
                max_width=panel_width, fill_width=True, anchor_bounds=viewport,
            )
            self._right.draw(
                text[1], window_size, anchor="center_right",
                max_width=panel_width, fill_width=True, anchor_bounds=viewport,
            )

    def release(self):
        self._left.release()
        self._right.release()
