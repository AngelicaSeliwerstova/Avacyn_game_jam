from dataclasses import dataclass
from pathlib import Path

import moderngl
import pygame


@dataclass(frozen=True)
class HudStyle:
    font_size: int = 18
    margin: int = 8


class TextOverlay:
    """Небольшая подпись поверх внутреннего кадра; текстура меняется вместе с текстом."""

    def __init__(self, context: moderngl.Context, style: HudStyle):
        self._context = context
        self._style = style
        self._font = pygame.font.Font(None, style.font_size)
        self._text = None
        self._wrap_width = None
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
             max_width: int | None = None):
        if not text:
            return
        if text != self._text or max_width != self._wrap_width:
            strings = text.splitlines()
            if max_width is not None:
                available = max(1, max_width - 2 * self._style.margin)
                strings = [line for string in strings for line in self._wrap_line(string, available)]
            lines = [self._font.render(line, False, (230, 228, 212)) for line in strings]
            padding = self._style.margin
            width = max(line.get_width() for line in lines) + 2 * padding
            height = len(lines) * self._font.get_linesize() + 2 * padding
            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            surface.fill((10, 10, 14, 205))
            for index, line in enumerate(lines):
                surface.blit(line, (padding, padding + index * self._font.get_linesize()))
            if self._texture is not None:
                self._texture.release()
            self._texture = self._context.texture(
                surface.get_size(), 4, pygame.image.tobytes(surface, "RGBA", True), alignment=1,
            )
            self._texture.filter = moderngl.NEAREST, moderngl.NEAREST
            self._text = text
            self._wrap_width = max_width
        width, height = self._texture.size
        margin = self._style.margin
        if anchor == "top_left":
            position = (margin, render_size[1] - height - margin)
        elif anchor == "bottom_right":
            position = (render_size[0] - width - margin, margin)
        elif anchor == "bottom_center":
            position = ((render_size[0] - width) // 2, margin)
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

    def _wrap_line(self, text: str, width: int) -> list[str]:
        lines, current = [], ""
        for word in text.split():
            candidate = f"{current} {word}" if current else word
            if current and self._font.size(candidate)[0] > width:
                lines.append(current)
                current = ""
            # Длинное слово тоже не должно выходить за границы кадра.
            for character in (" " if current else "") + word:
                if current and self._font.size(current + character)[0] > width:
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
