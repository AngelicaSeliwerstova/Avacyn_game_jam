"""Минимальная геометрия для проверок физики; в игре эти сцены недоступны."""

from config import settings
from engine.scene.box import Box
from engine.scene.level import Level


def create_level(name):
    if name == "stairs":
        boxes = [Box((0, (i + 1) * 0.25 / 2, 2 - (i + 0.5) * 0.8),
                     (3, (i + 1) * 0.25, 0.8)) for i in range(6)]
        boxes.append(Box((0, 0.75, -4.3), (5, 1.5, 3)))
        spawn = (0, settings.PLAYER_EYE_HEIGHT, 6)
    elif name == "corridor":
        boxes = [Box(((col + 0.5) * 2 - 10, 1.4, (row + 0.5) * 2 - 10), (2, 2.8, 2))
                 for row in range(10) for col in range(10)
                 if row in (0, 9) or col in (0, 9) or (row >= 3 and col >= 3)]
        spawn = (-6, settings.PLAYER_EYE_HEIGHT, 7)
    else:
        raise ValueError(name)
    return Level((20, 20), 1, tuple(boxes), spawn, (spawn[0], spawn[1], spawn[2] - 1),
                 settings.FLOOR_COLORS)
