import math
from array import array

import moderngl


class FloorMesh:
    """Пол на Y=0, собранный в один GPU-буфер. Цвета задаются уровнем."""

    def __init__(
        self,
        context: moderngl.Context,
        program: moderngl.Program,
        size: tuple[float, float],
        tile_size: float,
        colors: tuple[tuple[int, int, int], tuple[int, int, int]],
    ):
        width, depth = size
        if width <= 0 or depth <= 0 or tile_size <= 0:
            raise ValueError("Floor dimensions and tile size must be positive")
        normalized_colors = tuple(tuple(channel / 255 for channel in color) for color in colors)
        vertices = array("f")
        for ix in range(math.ceil(width / tile_size)):
            for iz in range(math.ceil(depth / tile_size)):
                x0 = -width / 2 + ix * tile_size
                z0 = -depth / 2 + iz * tile_size
                x1 = min(x0 + tile_size, width / 2)
                z1 = min(z0 + tile_size, depth / 2)
                corners = ((x0, 0, z0), (x0, 0, z1), (x1, 0, z1), (x1, 0, z0))
                color = normalized_colors[(ix + iz) % 2]
                for index in (0, 1, 2, 0, 2, 3):
                    vertices.extend((*corners[index], *color, 0.0, 1.0, 0.0))
        self._vertex_buffer = context.buffer(vertices.tobytes())
        try:
            self._vertex_array = context.vertex_array(
                program,
                [(self._vertex_buffer, "3f 3f 3f", "in_position", "in_color", "in_normal")],
            )
        except Exception:
            self._vertex_buffer.release()
            raise

    def render(self):
        self._vertex_array.render(mode=moderngl.TRIANGLES)

    def release(self):
        self._vertex_array.release()
        self._vertex_buffer.release()
