from array import array

import moderngl


class CubeMesh:
    """Куб со стороной 2: шесть цветных граней, по два треугольника на грань."""

    def __init__(self, context: moderngl.Context, program: moderngl.Program):
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
        for corners, color in faces:
            for index in (0, 1, 2, 0, 2, 3):
                vertices.extend((*corners[index], *color))
        # Данные передаются на видеокарту один раз при создании объекта.
        self._vertex_buffer = context.buffer(vertices.tobytes())
        try:
            self._vertex_array = context.vertex_array(
                program,
                [(self._vertex_buffer, "3f 3f", "in_position", "in_color")],
            )
        except Exception:
            self._vertex_buffer.release()
            raise

    def render(self):
        self._vertex_array.render(mode=moderngl.TRIANGLES)

    def release(self):
        self._vertex_array.release()
        self._vertex_buffer.release()
