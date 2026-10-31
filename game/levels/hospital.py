"""Трёхэтажная больница 43 × 29 м с непрерывной винтовой лестницей."""

from dataclasses import replace

from engine.scene.box import Box
from engine.scene.interaction import Interaction
from engine.scene.level import Level
from engine.scene.lighting import PointLight
from game.levels.spiral import SpiralStair
from game.levels.hospital_props import HospitalProps
from game.levels.hospital_storeys import assemble_storeys


OFFICE_DOORS = (-17, -10, -3, 4, 11, 18)
ROOM_NAMES = ("Кабинет врача", "Процедурная", "Смотровая", "Палата 01", "Склад", "Палата 02")
FLOOR_HEIGHT = 4.8
FLOOR_COUNT = 3
SLAB_THICKNESS = 0.24


def build_hospital(level: Level, peaceful: bool = False) -> Level:
    boxes, decorations, definitions, lights = [], [], [], []
    height = FLOOR_HEIGHT - SLAB_THICKNESS
    floor_count = 1 if peaceful else FLOOR_COUNT
    stair = SpiralStair(height=FLOOR_HEIGHT, flights=max(1, floor_count - 1))
    base_lights = level.lighting.lights if level.lighting else ()
    props = HospitalProps()

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

    def lamp(x, z, y=4.2, warm=False):
        color = (1.0, 0.83, 0.61) if warm else (0.72, 0.87, 0.84)
        index = len(base_lights) + len(lights)
        if peaceful:
            color = (1.0, 0.96, 0.87)
        lights.append(PointLight((x, y, z), color, (2.2 if peaceful else 3.5 if warm else 2.7), 8.5))
        decorations.append(Box((x, y + 0.12, z), (1.5, 0.1, 0.36), material="rust"))
        decorations.append(Box((x, y + 0.06, z), (1.32, 0.025, 0.24),
                               emission=tuple(c * 1.5 for c in color), emission_light=index))

    def desk(x, z, width=2.4, depth=0.9):
        box((x, 0.91, z), (width, 0.14, depth), "wood")
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
    wall("z", -21, -1, 9)
    wall("z", -21, 9, 14)
    partition("z", 21, -14, 14, (-3.5,), "side_entrance")
    partition("x", 14, -21, 21, (-0.5,), "main_entrance")
    for x in (-14, -7, 0, 7, 14):
        wall("z", x, -14, -6)
    partition("x", -6, -21, 21, OFFICE_DOORS, "office", ROOM_NAMES)
    partition("x", -2, -21, -5, (-18.5,), "corridor_stair")
    # Справа коридор свободно соединяется с зоной ожидания, без торчащей перегородки.
    # Центральная зона открыта из коридора до холла; служебные комнаты компактные.
    partition("z", -5, -2, 14, (10.5,), "stair_lounge", ("Лестничный зал",))
    partition("x", 3, -5, 2, (-1,), "security", ("Охрана",))
    wall("x", 9, -5, 2)
    wall("z", 2, 3, 9)
    partition("x", 3, 9, 19, (12,), "registration", ("Регистрация",))
    wall("x", 9, 9, 19)
    wall("z", 9, 3, 9)
    wall("z", 19, 3, 9)

    # Отдельная гостиная под лестничным залом и несколько небольших зон ожидания.
    props.sofa(-19.5, 11.5, 2.6, -90)
    props.sofa(-6.8, 12.0, 2.1, 90)
    props.sofa(-13, 12.8, 3.0)
    props.table(-13, 11.2, 2.0)
    props.plant(-12.6, 11.2, small=True, base=0.6)
    props.sofa(6.6, 12.8, 2.6)
    props.sofa(12.0, 12.8, 3.0)
    props.sofa(19.7, 11.2, 2.6, 90)
    props.sofa(15.8, 0.35, 3.0)
    props.sofa(-7.7, -2.7, 2.6)
    props.sofa(5.5, -1.65, 2.6)
    props.table(11.7, 10.9, 1.8)
    props.table(1.0, 0.9, 2.4, 0.95)
    props.table(5.8, 6.3, 0.7, 1.25)
    # Стойка регистрации — дерево, рабочие места, шкафы и боковое крыло.
    desk(14, 7.3, 7.3, 1.0)
    desk(17.4, 5.7, 0.8, 3.2)
    for x in (11.5, 14.5, 16.6):
        props.desk_details(x, 7.3)
        props.chair(x, 8.25, 180)
    props.cabinet(18.25, 4.4, 1.1)
    props.plant(10.2, 4.15)
    # Охрана со столом, стулом, монитором и шкафом для документов.
    desk(-1.4, 7.1, 3.2)
    props.desk_details(-1.4, 7.1)
    props.chair(-1.4, 8.15, 180)
    props.cabinet(-4.35, 5.1, 1.15)

    for x, z in ((-20, -2.7), (-15, -2.65), (-6.0, 1), (7.8, -1.65),
                 (19.8, -1.7), (-19.5, 8.7), (-6.5, 13.0), (3, 12.7),
                 (8.3, 10.7), (17.2, 12.9), (19.9, 8.4)):
        props.plant(x, z)

    for i, x in enumerate(OFFICE_DOORS):
        # Светлая плитка и разная обстановка отличают кабинеты друг от друга.
        props.part(x, -10, (0, 0.006, 0), (6.65, 0.012, 7.65),
                   "hospital_floor" if i in (0, 3, 5) else "hospital_tiles", detail=True)
        if i in (1, 2, 3, 5):
            bed(x - 1.45, -10.6)
            if i in (3, 5):
                bed(x + 1.45, -10.6)
                props.table(x, -12.6, 0.75, 0.6, 0.72)
        if i == 0:
            desk(x - 1.6, -10.6, 2.2)
            props.desk_details(x - 1.6, -10.6)
            props.chair(x - 1.6, -9.35)
            props.chair(x + 0.2, -9.8, -90)
            props.cabinet(x + 1.9, -12.7, 1.2, medical=False)
            props.plant(x + 1.9, -8.0)
        if i in (1, 2):
            desk(x + 1.5, -12.0, 2.0)
            props.cart(x + 1.8, -9.8)
            props.cabinet(x + 1.8, -7.4, 1.2)
        if i == 4:
            for offset in (-1.9, 0, 1.9):
                props.cabinet(x + offset, -12.7, 1.6, 2.3)
            props.cart(x + 1.8, -9)
        props.radiator(x, -13.65)
        plaque = Box((x + 1.35, 1.7, -5.84), (0.75, 0.28, 0.035), material="rust",
                     color=(0.27, 0.36, 0.31),
                     interaction=Interaction(ROOM_NAMES[i], ROOM_NAMES[i] + "."))
        boxes.append(plaque)
        lamp(x, -10)
    for x in (-17, -9, -1, 7, 16):
        lamp(x, -3.5)
    for x, z in ((-15, 11.5), (-5, 11.5), (5, 11.5), (15, 11.5), (-1, 4), (11, 5)):
        lamp(x, z, warm=z > 9)
    # Свет под галереей освещает ступени, не перекрываясь её плитой.
    lamp(-8.2, 6.7, y=4.15, warm=True)
    lamp(-18.5, 3, y=4.15, warm=True)
    # Высокие матовые окна в лестничном зале, с тёмными металлическими переплётами.
    for z in (1.2, 6.8):
        decorations.append(Box((-20.855, 2.6, z), (0.025, 2.6, 1.7),
                               color=(0.57, 0.66, 0.62), emission=(0.18, 0.23, 0.21)))
        for offset in (-0.9, 0, 0.9):
            box((-20.81, 2.6, z + offset), (0.08, 2.8, 0.07), "rust", (0.2, 0.24, 0.22))
        for y in (1.25, 2.2, 3.05, 3.95):
            box((-20.81, y, z), (0.08, 0.07, 1.85), "rust", (0.2, 0.24, 0.22))
    palette = ({"hospital_tiles": "hospital_tile_cream", "hospital_floor": "linoleum_blue_gray",
                "plaster": "wallpaper_aged", "concrete": "concrete_cracked",
                "rust": "metal_scratched_dark", "wood": "door_aged_wood"} if peaceful else
               {"hospital_tiles": "hospital_tile_ruined", "hospital_floor": "floor_tile_dirty",
                "plaster": "plaster_water_damage", "concrete": "concrete_cracked",
                "rust": "rust_iron_heavy", "wood": "wood_rotten"})
    for definition in definitions:
        definition["panel_material"] = "door_painted_teal" if peaceful else "door_aged_wood"
        definition["frame_material"] = "hospital_tile_cream" if peaceful else "concrete_cracked"
        if peaceful:
            definition["panel_color"] = (0.34, 0.52, 0.48)
    if peaceful:
        # В мирном мире доступны только помещения первого этажа.
        angle = 30
        radius = (stair.inner_radius + stair.outer_radius) / 2
        gate = Box(stair.point(angle, radius, 1.25),
                   (stair.outer_radius - stair.inner_radius, 2.5, 0.12),
                   yaw_degrees=-angle,
                   interaction=Interaction("Верхние этажи", "Пока туда нельзя."))
        level = replace(level, invisible_barriers=level.invisible_barriers + (gate,))
        # Верх обычных стен окрашен ровно, без трещин и облупившейся штукатурки.
        boxes = [replace(box, color=(0.82, 0.81, 0.74))
                 if box.material == "plaster" and box.size[1] > 1.2 else box for box in boxes]
    result = assemble_storeys(level, tuple(boxes) + tuple(props.boxes),
                            tuple(decorations) + tuple(props.decorations), definitions, lights,
                            stair, count=floor_count, material_map=palette,
                            ceiling_material="ceiling_acoustic_panels" if peaceful else "concrete")
    if any(obj.entity is not None and hasattr(obj.entity, "following") for obj in result.objects):
        from game.levels.hospital_navigation import build_hospital_navigation
        result = replace(result, navigation=build_hospital_navigation(result, stair, definitions))
    return result
