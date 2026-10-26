from dataclasses import dataclass
import math
from pathlib import Path

import moderngl
import pygame


@dataclass(frozen=True)
class TextureSettings:
    floor: Path | None
    wall: Path | None
    floor_world_size: float
    wall_world_size: float
    mipmaps: bool
    anisotropy: float

    def __post_init__(self):
        if any(not math.isfinite(value) or value <= 0
               for value in (self.floor_world_size, self.wall_world_size)):
            raise ValueError("Texture world sizes must be finite and positive")
        if not math.isfinite(self.anisotropy) or self.anisotropy < 1:
            raise ValueError("Texture anisotropy must be finite and at least 1")


class Texture2D:
    """Непрозрачная PNG-текстура: пиксели вблизи, mipmaps при уменьшении."""

    def __init__(self, context: moderngl.Context, path: Path,
                 mipmaps: bool, anisotropy: float):
        self.texture = None
        self.path = Path(path)
        image = pygame.image.load(str(self.path))
        self.size = image.get_size()
        self.levels = 1 + int(math.log2(max(self.size))) if mipmaps else 1
        try:
            self.texture = context.texture(
                self.size, components=3,
                data=pygame.image.tobytes(image, "RGB", True), alignment=1,
            )
            if mipmaps:
                self.texture.build_mipmaps()
            # build_mipmaps меняет оба фильтра, поэтому задаём их после генерации.
            self.texture.filter = (
                moderngl.LINEAR_MIPMAP_LINEAR if mipmaps else moderngl.NEAREST,
                moderngl.NEAREST,
            )
            self.texture.repeat_x = True
            self.texture.repeat_y = True
            # Без mipmaps оставляем честный nearest для сравнения и строгого PSX-режима.
            self.texture.anisotropy = min(anisotropy, context.max_anisotropy) if mipmaps else 1.0
        except Exception:
            self.release()
            raise

    def use(self, location: int = 0):
        self.texture.use(location=location)

    def release(self):
        if self.texture is not None:
            self.texture.release()
            self.texture = None
