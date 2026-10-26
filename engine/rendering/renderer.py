from pathlib import Path

import moderngl
import glm

from engine.rendering.meshes.cube import CubeMesh
from engine.scene.camera import Camera


class Renderer:
    """Управляет OpenGL-ресурсами и рисует содержимое кадра."""

    def __init__(
        self,
        viewport_size: tuple[int, int],
        background_color: tuple[int, int, int],
        opengl_version: tuple[int, int],
        camera: Camera,
    ):
        major, minor = opengl_version
        self.context = moderngl.create_context(require=major * 100 + minor * 10)
        self._program = None
        self._cube = None
        self._camera = camera

        try:
            self.context.viewport = (0, 0, *viewport_size)
            self.context.enable(moderngl.DEPTH_TEST)
            # Pygame использует 0–255, OpenGL принимает цвет в диапазоне 0–1.
            self._background_color = tuple(channel / 255 for channel in background_color)
            shader_dir = Path(__file__).resolve().parent / "shaders"
            self._program = self.context.program(
                vertex_shader=(shader_dir / "color.vert").read_text(encoding="utf-8"),
                fragment_shader=(shader_dir / "color.frag").read_text(encoding="utf-8"),
            )
            # Куб пока находится в начале координат без поворота и масштаба.
            self._program["m_model"].write(glm.mat4(1.0))
            width, height = viewport_size
            self._program["m_projection"].write(camera.projection_matrix(width / height))
            self._cube = CubeMesh(self.context, self._program)
        except Exception:
            self.release()
            raise

    def render(self):
        self.context.clear(*self._background_color, depth=1.0)
        self._program["m_view"].write(self._camera.view_matrix)
        self._cube.render()

    def release(self):
        if self._cube is not None:
            self._cube.release()
            self._cube = None
        if self._program is not None:
            self._program.release()
            self._program = None
        if self.context is not None:
            self.context.release()
            self.context = None
