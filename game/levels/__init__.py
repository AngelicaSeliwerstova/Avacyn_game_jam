"""Карты геймджема из resources/levels/<name>.json."""

from pathlib import Path

from engine.scene.level import Level
from game.levels.location import load_location


LEVELS_ROOT = Path(__file__).resolve().parents[2] / "resources" / "levels"


def create_level(name: str) -> Level:
    if not isinstance(name, str) or not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in name):
        raise ValueError(f"Invalid level name: {name!r}")
    path = LEVELS_ROOT / f"{name}.json"
    if not path.is_file():
        raise ValueError(f"Unknown level: {name!r}")
    return load_location(path)
