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

    def draw(self, text: str, render_size: tuple[int, int]):
        if not text:
            return
        if text != self._text:
            lines = [self._font.render(line, False, (230, 228, 212)) for line in text.splitlines()]
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
        width, height = self._texture.size
        margin = self._style.margin
        self._context.viewport = (margin, render_size[1] - height - margin, width, height)
        self._context.disable(moderngl.DEPTH_TEST)
        self._context.enable(moderngl.BLEND)
        self._context.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        try:
            self._texture.use(location=0)
            self._vertices.render(mode=moderngl.TRIANGLES, vertices=3)
        finally:
            self._context.disable(moderngl.BLEND)

    def release(self):
        for name in ("_texture", "_vertices", "_program"):
            resource = getattr(self, name)
            if resource is not None:
                resource.release()
                setattr(self, name, None)
