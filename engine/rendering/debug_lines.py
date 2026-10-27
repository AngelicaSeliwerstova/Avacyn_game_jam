from array import array
from pathlib import Path

import moderngl

from engine.debug.geometry import DebugPath


class DebugLineRenderer:
    """Отладочные линии поверх сцены, без освещения и проверки глубины."""

    def __init__(self, context):
        self._context = context
        self._program = self._buffer = self._vertices = None
        self._paths = None
        self._count = 0
        try:
            shaders = Path(__file__).resolve().parent / "shaders"
            self._program = context.program(
                vertex_shader=(shaders / "debug_line.vert").read_text(encoding="utf-8"),
                fragment_shader=(shaders / "debug_line.frag").read_text(encoding="utf-8"),
            )
            self._buffer = context.buffer(reserve=48, dynamic=True)
            self._vertices = context.vertex_array(self._program,
                                                 [(self._buffer, "3f 3f", "in_position", "in_color")])
        except Exception:
            self.release()
            raise

    def draw(self, paths: tuple[DebugPath, ...], view_projection):
        if paths != self._paths:
            data = array("f")
            for path in paths:
                for a, b in zip(path.points, path.points[1:]):
                    data.extend((*a, *path.color, *b, *path.color))
            self._count = len(data) // 6
            if data:
                raw = data.tobytes()
                if len(raw) > self._buffer.size:
                    self._buffer.orphan(max(len(raw), self._buffer.size * 2))
                self._buffer.write(raw)
            self._paths = paths
        if self._count:
            self._program["m_view_projection"].write(view_projection.to_bytes())
            self._context.disable(moderngl.DEPTH_TEST | moderngl.BLEND)
            self._vertices.render(mode=moderngl.LINES, vertices=self._count)

    def release(self):
        for name in ("_vertices", "_buffer", "_program"):
            resource = getattr(self, name)
            if resource is not None:
                resource.release()
                setattr(self, name, None)
