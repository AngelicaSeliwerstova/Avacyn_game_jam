from pathlib import Path

import moderngl

from engine.rendering.meshes.triangle import TriangleMesh


class Renderer:
    """Управляет OpenGL-ресурсами и рисует содержимое кадра."""

    def __init__(
        self,
        viewport_size: tuple[int, int],
        background_color: tuple[int, int, int],
        opengl_version: tuple[int, int],
    ):
        major, minor = opengl_version
        self.context = moderngl.create_context(require=major * 100 + minor * 10)
        self._program = None
        self._triangle = None

        try:
            self.context.viewport = (0, 0, *viewport_size)
            # Pygame использует 0–255, OpenGL принимает цвет в диапазоне 0–1.
            self._background_color = tuple(channel / 255 for channel in background_color)
            shader_dir = Path(__file__).resolve().parent / "shaders"
            self._program = self.context.program(
                vertex_shader=(shader_dir / "triangle.vert").read_text(encoding="utf-8"),
                fragment_shader=(shader_dir / "triangle.frag").read_text(encoding="utf-8"),
            )
            self._triangle = TriangleMesh(self.context, self._program)
        except Exception:
            self.release()
            raise

    def render(self):
        self.context.clear(*self._background_color)
        self._triangle.render()

    def release(self):
        if self._triangle is not None:
            self._triangle.release()
            self._triangle = None
        if self._program is not None:
            self._program.release()
            self._program = None
        if self.context is not None:
            self.context.release()
            self.context = None
