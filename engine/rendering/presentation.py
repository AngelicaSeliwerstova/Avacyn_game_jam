from pathlib import Path

import moderngl


def integer_viewport(
    window_size: tuple[int, int], render_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    """Центрированный прямоугольник с целым масштабом внутреннего кадра."""
    width, height = window_size
    render_width, render_height = render_size
    if min(render_size) <= 0 or min(window_size) < 0:
        raise ValueError("Render size must be positive and window size nonnegative")
    scale = min(width // render_width, height // render_height)
    if scale < 1:
        # Возможный промежуточный размер при сворачивании окна.
        return 0, 0, 0, 0
    scaled_width, scaled_height = render_width * scale, render_height * scale
    return (
        (width - scaled_width) // 2, (height - scaled_height) // 2,
        scaled_width, scaled_height,
    )


class PixelPresenter:
    """Выводит готовую текстуру в окно, сохраняя чёткие квадратные пиксели."""

    def __init__(self, context: moderngl.Context):
        self._context = context
        self._program = None
        self._vertex_array = None
        try:
            shader_dir = Path(__file__).resolve().parent / "shaders"
            self._program = context.program(
                vertex_shader=(shader_dir / "present.vert").read_text(encoding="utf-8"),
                fragment_shader=(shader_dir / "present.frag").read_text(encoding="utf-8"),
            )
            self._program["scene_texture"].value = 0
            self._vertex_array = context.vertex_array(self._program, [])
        except Exception:
            self.release()
            raise

    def present(
        self,
        texture: moderngl.Texture,
        target: moderngl.Framebuffer,
        window_size: tuple[int, int],
    ):
        target.use()
        self._context.viewport = (0, 0, *window_size)
        self._context.scissor = None
        self._context.disable(moderngl.DEPTH_TEST | moderngl.BLEND)
        self._context.clear(0.0, 0.0, 0.0, 1.0)
        viewport = integer_viewport(window_size, texture.size)
        if viewport[2] == 0:
            return
        self._context.viewport = viewport
        texture.use(location=0)
        self._vertex_array.render(mode=moderngl.TRIANGLES, vertices=3)

    def release(self):
        if self._vertex_array is not None:
            self._vertex_array.release()
            self._vertex_array = None
        if self._program is not None:
            self._program.release()
            self._program = None
