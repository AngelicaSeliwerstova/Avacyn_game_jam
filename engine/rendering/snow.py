from array import array
from math import radians, tan
from pathlib import Path

import moderngl

from engine.particles.snow import Snowfall
from engine.scene.camera import Camera


class SnowRenderer:
    """Мягкие точечные частицы с перспективой и глубиной общей 3D-сцены."""

    def __init__(self, context: moderngl.Context, snow: Snowfall, camera: Camera,
                 render_size: tuple[int, int]):
        self._context = context
        self._snow = snow
        self._program = None
        self._buffer = None
        self._vertices = None
        try:
            shaders = Path(__file__).resolve().parent / "shaders"
            self._program = context.program(
                vertex_shader=(shaders / "snow.vert").read_text(encoding="utf-8"),
                fragment_shader=(shaders / "snow.frag").read_text(encoding="utf-8"),
            )
            width, height = render_size
            self._program["m_projection"].write(camera.projection_matrix(width / height))
            self._program["point_scale"].value = (
                snow.settings.flake_size * height / (2 * tan(radians(camera.fov_degrees) / 2))
            )
            self._program["snow_color"].value = tuple(c / 255 for c in snow.settings.color)
            self._program["snow_height"].value = snow.settings.height
            self._buffer = context.buffer(reserve=snow.settings.count * 3 * 4, dynamic=True)
            self._vertices = context.vertex_array(
                self._program, [(self._buffer, "3f", "in_position")],
            )
        except Exception:
            self.release()
            raise

    @property
    def particle_count(self) -> int:
        return self._snow.settings.count

    def render(self, camera: Camera):
        positions = array("f", (value for position in self._snow.positions for value in position))
        self._buffer.write(positions.tobytes())
        self._program["m_view"].write(camera.view_matrix)
        self._context.enable(moderngl.BLEND | moderngl.PROGRAM_POINT_SIZE)
        self._context.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        # Стены закрывают снег; прозрачные края снежинок не закрывают другие частицы.
        target = self._context.fbo
        target.depth_mask = False
        try:
            self._vertices.render(mode=moderngl.POINTS)
        finally:
            target.depth_mask = True
            self._context.disable(moderngl.BLEND | moderngl.PROGRAM_POINT_SIZE)

    def release(self):
        for name in ("_vertices", "_buffer", "_program"):
            resource = getattr(self, name)
            if resource is not None:
                resource.release()
                setattr(self, name, None)
