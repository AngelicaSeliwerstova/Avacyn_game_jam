from pathlib import Path

from config import settings
from engine.scene.model import ModelComponent
from engine.scene.transform import Transform


def create_character_model():
    root = Path(__file__).resolve().parents[2] / "resources" / "models"
    return ModelComponent(
        source_path=None if settings.PLAYER_MODEL is None else root / settings.PLAYER_MODEL,
        local_transform=Transform(position=settings.PLAYER_MODEL_OFFSET,
                                  rotation=settings.PLAYER_MODEL_ROTATION,
                                  scale=(settings.PLAYER_MODEL_SCALE,) * 3),
    )
