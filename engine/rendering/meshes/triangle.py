from array import array

import moderngl


class TriangleMesh:
    """Три вершины: у каждой есть позиция XYZ и цвет RGB."""

    def __init__(self, context: moderngl.Context, program: moderngl.Program):
        vertices = array("f", [
            # X,    Y,    Z,    R,    G,    B
            -0.6, -0.5,  0.0,  1.0,  0.2,  0.2,
             0.6, -0.5,  0.0,  0.2,  1.0,  0.2,
             0.0,  0.6,  0.0,  0.2,  0.4,  1.0,
        ])
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
