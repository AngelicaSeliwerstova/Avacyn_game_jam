"""Первый этаж больницы: план 43 × 29 м и двухсветный лестничный зал."""

from dataclasses import replace
import math

from engine.scene.box import Box
from engine.scene.interaction import Interaction
from engine.scene.level import Level
from engine.scene.lighting import Lighting, PointLight
from game.levels.objects import build_objects
from game.levels.spiral import SpiralStair


OFFICE_DOORS = (-17, -10, -3, 4, 11, 18)
CORRIDOR_DOORS = (-13, -1, 11)
LOBBY_DOORS = (-12, -1, 12)
ROOM_NAMES = ("Treatment room", "Examination room", "Patient ward 01",
              "Patient ward 02", "Doctor's office", "Medical storage")


def build_hospital(level: Level) -> Level:
    boxes, decorations, definitions, lights = [], [], [], []
    height = 4.8
    stair = SpiralStair()
    base_lights = level.lighting.lights if level.lighting else ()

    def box(position, size, material="concrete", color=None, yaw=0):
        item = Box(position, size, material=material, color=color, yaw_degrees=yaw)
        boxes.append(item)
        return item

    def wall(axis, fixed, start, end, tall=height):
        if end <= start:
            return
        for low, high, material in (
            (0, 1.35, "hospital_tiles"),
            (1.35, tall, "plaster"),
        ):
            if high <= low:
                continue
            center = ((start + end) / 2, (low + high) / 2, fixed)
            size = (end - start, high - low, 0.24)
            if axis == "z":
                center = (fixed, center[1], center[0])
                size = (0.24, size[1], size[0])
            box(center, size, material)
        center = ((start + end) / 2, 0.075, fixed)
        size = (end - start, 0.15, 0.28)
        if axis == "z":
            center, size = (fixed, 0.075, center[0]), (0.28, 0.15, end - start)
        box(center, size, "rust", (0.24, 0.27, 0.25))

    def partition(axis, fixed, start, end, doors, prefix, names=()):
        cursor = start
        for index, center in enumerate(doors):
            wall(axis, fixed, cursor, center - 0.95)
            position = (center, 0, fixed) if axis == "x" else (fixed, 0, center)
            definitions.append({"id": f"{prefix}_{index}", "type": "door", "position": position,
                                "name": names[index] if names else prefix.replace("_", " ").title(),
                                "width": 1.65, "height": 2.65, "opening_width": 1.9,
                                "wall_height": height, "axis": axis, "open_seconds": 0.6})
            cursor = center + 0.95
        wall(axis, fixed, cursor, end)

    def lamp(x, z, y=4.45, warm=False):
        color = (1.0, 0.83, 0.61) if warm else (0.72, 0.87, 0.84)
        index = len(base_lights) + len(lights)
        lights.append(PointLight((x, y, z), color, 2.8 if warm else 2.2, 7.0))
        decorations.append(Box((x, y + 0.12, z), (1.5, 0.1, 0.36), material="rust"))
        decorations.append(Box((x, y + 0.06, z), (1.32, 0.025, 0.24),
                               emission=tuple(c * 1.5 for c in color), emission_light=index))

    def bench(x, z, width=4.6):
        box((x, 0.48, z), (width, 0.25, 0.9), "wood", (0.34, 0.4, 0.34))
        box((x, 0.94, z + 0.4), (width, 0.7, 0.15), "wood", (0.34, 0.4, 0.34))
        for side in (-1, 1):
            box((x + side * (width / 2 - 0.12), 0.5, z), (0.18, 0.9, 1.0), "rust", (0.25, 0.28, 0.26))

    def desk(x, z, width=2.4, depth=0.9):
        box((x, 0.91, z), (width, 0.14, depth), "wood", (0.51, 0.42, 0.3))
        for side in (-1, 1):
            box((x + side * (width / 2 - 0.27), 0.43, z), (0.4, 0.86, depth * 0.85), "plaster")

    def bed(x, z):
        box((x, 0.45, z), (1.2, 0.22, 2.2), "rust", (0.48, 0.51, 0.47))
        box((x, 0.66, z), (1.14, 0.2, 2.05), "plaster", (0.78, 0.77, 0.65))
        box((x, 0.82, z - 0.7), (0.85, 0.12, 0.48), "plaster", (0.86, 0.84, 0.75))
        for side in (-1, 1):
            box((x + side * 0.5, 0.25, z), (0.07, 0.5, 1.85), "rust")
        box((x, 0.72, z - 1.05), (1.2, 0.85, 0.06), "rust")

    # Внешняя оболочка и шесть кабинетов вдоль северного фасада.
    wall("x", -14, -21, 21)
    wall("z", -21, -14, -1)
    wall("z", -21, -1, 9, tall=9.6)
    wall("z", -21, 9, 14)
    partition("z", 21, -14, 14, (-3.5,), "side_entrance")
    partition("x", 14, -21, 21, (-0.5,), "main_entrance")
    for x in (-14, -7, 0, 7, 14):
        wall("z", x, -14, -6)
    partition("x", -6, -21, 21, OFFICE_DOORS, "office", ROOM_NAMES)
    partition("x", -1, -21, 21, CORRIDOR_DOORS, "corridor")
    partition("x", 9, -21, 21, LOBBY_DOORS, "lobby")
    wall("z", -5, -1, 9)
    partition("z", 5, -1, 9, (5,), "registration")

    # Потолок первого этажа оставляет лестничный зал открытым на два уровня.
    box((0, 4.94, -7.5), (42, 0.28, 13), "concrete")
    box((8, 4.94, 4), (26, 0.28, 10), "concrete")
    box((0, 4.94, 11.5), (42, 0.28, 5), "concrete")
    box((-13, 9.74, 4), (16, 0.28, 10), "concrete")
    # Верхние стенки двухсветного зала.
    for axis, fixed, start, end in (("x", -1, -21, -5), ("x", 9, -21, -5), ("z", -5, -1, 9)):
        pos = ((start + end) / 2, 7.2, fixed)
        size = (end - start, 4.8, 0.24)
        if axis == "z":
            pos, size = (fixed, 7.2, pos[0]), (0.24, 4.8, end - start)
        box(pos, size, "plaster")

    boxes.extend(stair.build())
    # Галерея: прямые края у стен и круглый вырез над винтовым маршем.
    cx, cz = stair.center
    half = 4.6
    for x1, x2, z1, z2 in ((-21, cx - half, -1, 9), (cx + half, -5, -1, 9),
                            (cx - half, cx + half, -1, cz - half),
                            (cx - half, cx + half, cz + half, 9)):
        box(((x1 + x2) / 2, 4.68, (z1 + z2) / 2), (x2 - x1, 0.24, z2 - z1), "concrete")
    count = 64
    for i in range(count):
        angle = (i + 0.5) * 360 / count
        rad = math.radians(angle)
        outer = half / max(abs(math.cos(rad)), abs(math.sin(rad)))
        inner = 4.35
        radius = (inner + outer) / 2
        depth = 2 * outer * math.tan(math.pi / count) + 0.025
        box(stair.point(angle, radius, 4.68), (outer - inner + 0.025, 0.24, depth),
            "concrete", yaw=-angle)
        # Выход лестницы на восточную часть галереи остаётся без ограждения.
        if not 20 < angle < 75:
            radius = 4.34
            depth = 2 * radius * math.tan(math.pi / count) + 0.02
            box(stair.point(angle, radius, 5.8), (0.065, 0.07, depth), "rust", (0.3, 0.29, 0.26), -angle)
            if i % 3 == 0:
                box(stair.point(angle, radius, 5.28), (0.06, 1.0, 0.06), "rust")

    # Холл, стойка регистрации и охрана.
    bench(-15, 11.7)
    bench(14.5, 11.7, 5.5)
    desk(12, 2.0, 6.5, 1.15)
    desk(15.8, 4.1, 1.1, 5.3)
    for x in (9, 12, 15):
        box((x, 1.45, 1.95), (0.7, 0.55, 0.12), "rust", (0.23, 0.27, 0.24))
    desk(-0.7, 2.4, 3.2)
    box((-3.8, 1.05, 0.1), (0.65, 2.1, 1.6), "rust", (0.47, 0.53, 0.48))
    box((-0.7, 1.36, 2.35), (0.7, 0.6, 0.16), "rust", (0.23, 0.27, 0.24))
    bench(16.8, 6.8, 3.0)

    for i, x in enumerate(OFFICE_DOORS):
        if i in (0, 1, 2, 3):
            bed(x - 1.45, -10.6)
            if i in (2, 3):
                bed(x + 1.45, -10.6)
        if i in (0, 1, 4):
            desk(x + 1.4, -12.1, 2.0)
        if i == 5:
            for offset in (-1.9, 0, 1.9):
                box((x + offset, 1.15, -12.5), (1.4, 2.3, 0.65), "rust", (0.48, 0.56, 0.51))
        plaque = Box((x + 1.35, 1.7, -5.84), (0.75, 0.28, 0.035), material="rust",
                     color=(0.27, 0.36, 0.31),
                     interaction=Interaction(ROOM_NAMES[i], ROOM_NAMES[i] + "."))
        boxes.append(plaque)
        lamp(x, -10)
    for x in (-17, -9, -1, 7, 16):
        lamp(x, -3.5)
    for x, z in ((-15, 11.5), (-5, 11.5), (5, 11.5), (15, 11.5), (-1, 4), (11, 5)):
        lamp(x, z, warm=z > 9)
    lamp(-13, 4, y=9.2, warm=True)
    for x, z in ((-18.5, 4), (-7.0, 4)):
        lamp(x, z, y=9.2, warm=True)
    # Свет под галереей освещает ступени, не перекрываясь её плитой.
    lamp(-8.2, 6.7, y=4.25, warm=True)
    lamp(-18.5, 3, y=4.25, warm=True)
    # Высокие матовые окна в лестничном зале, с тёмными металлическими переплётами.
    for z in (1.2, 6.8):
        decorations.append(Box((-20.855, 4.2, z), (0.025, 4.6, 1.7),
                               color=(0.57, 0.66, 0.62), emission=(0.18, 0.23, 0.21)))
        for offset in (-0.9, 0, 0.9):
            box((-20.81, 4.2, z + offset), (0.08, 4.8, 0.07), "rust", (0.2, 0.24, 0.22))
        for y in (1.85, 3.0, 4.2, 5.4, 6.55):
            box((-20.81, y, z), (0.08, 0.07, 1.85), "rust", (0.2, 0.24, 0.22))
    return replace(level, boxes=tuple(boxes) + level.boxes,
                   decorations=tuple(decorations) + level.decorations,
                   objects=build_objects(definitions) + level.objects,
                   lighting=Lighting(level.lighting.ambient if level.lighting else (0.14, 0.16, 0.15),
                                     base_lights + tuple(lights)),
                   floor_heights=(0.0, height), floor_labels=("1", "2"),
                   floor_hints=("", ""))
