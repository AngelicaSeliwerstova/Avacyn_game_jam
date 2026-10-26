from pathlib import Path

from config import settings
from engine.rendering.texture import TextureMaterial, TextureSettings


def create_texture_settings() -> TextureSettings | None:
    if not settings.TEXTURES_ENABLED:
        return None
    if settings.TEXTURE_RESOLUTION not in (128, 256):
        raise ValueError("Texture resolution must be 128 or 256")
    root = Path(__file__).resolve().parents[1] / "resources" / "textures"

    def resource(path: str) -> Path:
        return root / path.format(size=settings.TEXTURE_RESOLUTION)

    return TextureSettings(
        floor=None if settings.FLOOR_TEXTURE is None else resource(settings.FLOOR_TEXTURE),
        wall=None if settings.WALL_TEXTURE is None else resource(settings.WALL_TEXTURE),
        floor_world_size=settings.FLOOR_TEXTURE_WORLD_SIZE,
        wall_world_size=settings.WALL_TEXTURE_WORLD_SIZE,
        mipmaps=settings.TEXTURE_MIPMAPS, anisotropy=settings.TEXTURE_ANISOTROPY,
        materials=tuple(TextureMaterial(name, resource(path), world_size)
                        for name, (path, world_size) in settings.MATERIAL_TEXTURES.items()),
    )
