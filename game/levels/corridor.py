from pathlib import Path

from config import settings
from engine.scene.level import Level
from engine.scene.tiled_level import load_tiled_level


def create_corridor_level() -> Level:
    map_path = Path(__file__).resolve().parents[2] / "resources" / "levels" / "corridor.tmx"
    return load_tiled_level(
        map_path, eye_height=settings.PLAYER_EYE_HEIGHT, floor_colors=settings.FLOOR_COLORS,
    )
