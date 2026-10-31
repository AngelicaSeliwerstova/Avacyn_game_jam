from array import array

import moderngl


class CubeMesh:
    """Куб со стороной 2: шесть цветных граней, по два треугольника на грань."""

    def __init__(self, context: moderngl.Context, program: moderngl.Program, *, position_only=False,
                 instance_buffer=None):
        # Четыре угла каждой грани перечислены против часовой стрелки снаружи.
        faces = (
            (((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)), (0.85, 0.35, 0.18)),
            (((1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)), (0.45, 0.25, 0.65)),
            (((1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1)), (0.18, 0.55, 0.70)),
            (((-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)), (0.25, 0.65, 0.35)),
            (((-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1)), (0.95, 0.80, 0.50)),
            (((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)), (0.20, 0.25, 0.35)),
        )
        vertices = array("f")
        normals = ((0, 0, 1), (0, 0, -1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0))
        for (corners, color), normal in zip(faces, normals):
            for index in (0, 1, 2, 0, 2, 3):
                vertices.extend((*corners[index], *color, *normal))
        # Данные передаются на видеокарту один раз при создании объекта.
        self.triangle_count = len(vertices) // 27
        self._vertex_buffer = context.buffer(vertices.tobytes())
        try:
            content = ([(self._vertex_buffer, "3f 24x", "in_position")] if position_only else
                       [(self._vertex_buffer, "3f 3f 3f", "in_position", "in_color", "in_normal")])
            if instance_buffer is not None:
                content.append((instance_buffer, "4f 4f 4f 4f /i", "model_col0", "model_col1",
                                "model_col2", "model_col3"))
            self._vertex_array = context.vertex_array(
                program, content,
            )
        except Exception:
            self._vertex_buffer.release()
            raise

    def render(self, instances=1):
        self._vertex_array.render(mode=moderngl.TRIANGLES, instances=instances)

    def release(self):
        self._vertex_array.release()
        self._vertex_buffer.release()
