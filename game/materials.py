from pathlib import Path

from config import settings
from engine.rendering.texture import TextureSettings


def create_texture_settings() -> TextureSettings | None:
    if not settings.TEXTURES_ENABLED:
        return None
    root = Path(__file__).resolve().parents[1] / "resources" / "textures"
    return TextureSettings(
        floor=None if settings.FLOOR_TEXTURE is None else root / settings.FLOOR_TEXTURE,
        wall=None if settings.WALL_TEXTURE is None else root / settings.WALL_TEXTURE,
        floor_world_size=settings.FLOOR_TEXTURE_WORLD_SIZE,
        wall_world_size=settings.WALL_TEXTURE_WORLD_SIZE,
        mipmaps=settings.TEXTURE_MIPMAPS, anisotropy=settings.TEXTURE_ANISOTROPY,
    )
