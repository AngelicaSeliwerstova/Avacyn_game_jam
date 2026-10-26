"""Создание игровых и тестовых уровней."""

from engine.scene.level import Level
from game.levels.corridor import create_corridor_level
from game.levels.demo import create_demo_level
from game.levels.stairs import create_stairs_level


def create_level(name: str) -> Level:
    if name == "stairs":
        return create_stairs_level()
    if name == "corridor":
        return create_corridor_level()
    if name == "demo":
        return create_demo_level()
    raise ValueError(f"Unknown level: {name!r}. Choose 'stairs', 'corridor' or 'demo'.")
