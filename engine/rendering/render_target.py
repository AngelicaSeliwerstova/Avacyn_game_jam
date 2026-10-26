import moderngl


class RenderTarget:
    """Фиксированный кадр сцены: цветовая текстура и буфер глубины."""

    def __init__(self, context: moderngl.Context, size: tuple[int, int], *,
                 with_depth: bool = True, dtype: str = "f1"):
        if min(size) <= 0:
            raise ValueError("Render target dimensions must be positive")
        self.size = size
        self.color = None
        self.depth = None
        self.framebuffer = None
        try:
            self.color = context.texture(size, components=4, dtype=dtype)
            self.color.filter = (moderngl.NEAREST, moderngl.NEAREST)
            self.color.repeat_x = False
            self.color.repeat_y = False
            if with_depth:
                self.depth = context.depth_renderbuffer(size)
            self.framebuffer = context.framebuffer(
                color_attachments=(self.color,), depth_attachment=self.depth,
            )
        except Exception:
            self.release()
            raise

    def release(self):
        for name in ("framebuffer", "depth", "color"):
            resource = getattr(self, name)
            if resource is not None:
                resource.release()
                setattr(self, name, None)
