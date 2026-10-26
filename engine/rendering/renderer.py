from pathlib import Path

import moderngl
import glm

from engine.rendering.meshes.cube import CubeMesh
from engine.rendering.meshes.floor import FloorMesh
from engine.rendering.presentation import PixelPresenter
from engine.rendering.render_target import RenderTarget
from engine.scene.camera import Camera
from engine.scene.level import Level


class Renderer:
    """Управляет OpenGL-ресурсами и рисует содержимое кадра."""

    def __init__(
        self,
        render_size: tuple[int, int],
        background_color: tuple[int, int, int],
        opengl_version: tuple[int, int],
        camera: Camera,
        level: Level,
    ):
        major, minor = opengl_version
        self.context = moderngl.create_context(require=major * 100 + minor * 10)
        self._program = None
        self._cube = None
        self._floor = None
        self._render_target = None
        self._presenter = None
        self._camera = camera
        self._level = level

        try:
            # Pygame использует 0–255, OpenGL принимает цвет в диапазоне 0–1.
            self._background_color = tuple(channel / 255 for channel in background_color)
            shader_dir = Path(__file__).resolve().parent / "shaders"
            self._program = self.context.program(
                vertex_shader=(shader_dir / "color.vert").read_text(encoding="utf-8"),
                fragment_shader=(shader_dir / "color.frag").read_text(encoding="utf-8"),
            )
            width, height = render_size
            self._program["m_projection"].write(camera.projection_matrix(width / height))
            self._cube = CubeMesh(self.context, self._program)
            self._floor = FloorMesh(
                self.context, self._program, level.floor_size, level.floor_tile_size,
            )
            self._render_target = RenderTarget(self.context, render_size)
            self._presenter = PixelPresenter(self.context)
        except Exception:
            self.release()
            raise

    def render(self, window_size: tuple[int, int]):
        self._render_target.framebuffer.use()
        self.context.viewport = (0, 0, *self._render_target.size)
        self.context.enable(moderngl.DEPTH_TEST)
        self.context.clear(*self._background_color, alpha=1.0, depth=1.0)
        self._program["m_view"].write(self._camera.view_matrix)
        self._program["m_model"].write(glm.mat4(1.0))
        self._floor.render()
        for box in self._level.boxes:
            self._program["m_model"].write(box.model_matrix)
            self._cube.render()
        self._presenter.present(self._render_target.color, self.context.screen, window_size)

    def release(self):
        if self._presenter is not None:
            self._presenter.release()
            self._presenter = None
        if self._render_target is not None:
            self._render_target.release()
            self._render_target = None
        if self._floor is not None:
            self._floor.release()
            self._floor = None
        if self._cube is not None:
            self._cube.release()
            self._cube = None
        if self._program is not None:
            self._program.release()
            self._program = None
        if self.context is not None:
            self.context.release()
            self.context = None
