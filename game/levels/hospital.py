"""Трёхэтажная больница с хирургическим вторым этажом 60 × 48 м."""

from dataclasses import replace

from engine.scene.box import Box
from engine.scene.interaction import Interaction
from engine.scene.level import Level
from engine.scene.lighting import PointLight
from game.levels.spiral import SpiralStair
from game.levels.hospital_props import HospitalProps
from game.levels.hospital_storeys import assemble_storeys
from game.levels.hospital_surgery import SURGERY_FLOOR_SIZE, build_surgical_floor
from game.levels.hospital_patient import PATIENT_FLOOR_SIZE, build_patient_floor
from game.levels.hospital_finishes import hospital_palette


OFFICE_DOORS = (-17, -10, -3, 4, 11, 18)
ROOM_NAMES = ("Кабинет врача", "Процедурная", "Смотровая", "Склад", "Палата 01", "Палата 02")
FLOOR_HEIGHT = 4.8
FLOOR_COUNT = 3
SLAB_THICKNESS = 0.24


def build_hospital(level: Level, peaceful: bool = False) -> Level:
    boxes, decorations, definitions, lights = [], [], [], []
    height = FLOOR_HEIGHT - SLAB_THICKNESS
    floor_count = FLOOR_COUNT
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
        box(center, size, "skirting")

    def partition(axis, fixed, start, end, doors, prefix, names=(), **door_options):
        cursor = start
        for index, center in enumerate(doors):
            wall(axis, fixed, cursor, center - 0.95)
            position = (center, 0, fixed) if axis == "x" else (fixed, 0, center)
            definitions.append({"id": f"{prefix}_{index}", "type": "door", "position": position,
                                "name": names[index] if names else prefix.replace("_", " ").title(),
                                "width": 1.65, "height": 2.65, "opening_width": 1.9,
                                "wall_height": height, "axis": axis, "open_seconds": 0.6})
            definitions[-1].update(door_options)
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
        with props.authored_group("desk", x, z, extra_boxes=boxes):
            box((x, 0.91, z), (width, 0.14, depth), "wood")
            for side in (-1, 1):
                box((x + side * (width / 2 - 0.27), 0.43, z), (0.4, 0.86, depth * 0.85), "plaster")

    def bed(x, z):
        with props.authored_group("bed", x, z, extra_boxes=boxes):
            # Leave only the radiator's depth behind the headboard.
            with props.against_wall("z", -13.88, gap=0.4, extra_boxes=boxes):
                box((x, 0.45, z), (1.2, 0.22, 2.2), "medical_enamel")
                box((x, 0.66, z), (1.14, 0.2, 2.05), "bed_linen")
                box((x, 0.82, z - 0.7), (0.85, 0.12, 0.48), "bed_linen")
                for side in (-1, 1):
                    box((x + side * 0.5, 0.25, z), (0.07, 0.5, 1.85), "rust")
                box((x, 0.72, z - 1.05), (1.2, 0.85, 0.06), "medical_enamel")
                props.bed_details(x, z, mattress_top=0.76)

    # Внешняя оболочка и шесть кабинетов вдоль северного фасада.
    wall("x", -14, -21, 21)
    wall("z", -21, -14, -1)
    wall("z", -21, -1, 9)
    wall("z", -21, 9, 14)
    partition("z", 21, -14, 14, (-3.5,), "side_entrance")
    partition("x", 14, -21, 21, (-0.5,), "main_entrance")
    for definition in definitions:
        if definition["id"] in ("side_entrance_0", "main_entrance_0"):
            definition.update(
                elevator=True,
                name="Лифт",
                warning="Лифтом лучше не пользоваться.",
            )
    for x in (-14, -7, 0, 7, 14):
        wall("z", x, -14, -6)
    partition("x", -6, -21, 21, OFFICE_DOORS, "office", ROOM_NAMES)
    # The reference has a solid north wall at the stair and an open south lobby.
    wall("x", -2, -21, -6)
    wall("z", -6, -2, 8)
    # Security connects the corridor and the entrance hall through two doors.
    partition("x", 0, -6, 0, (-3,), "security", ("Охрана — вход из коридора",), open_angle=-90)
    partition("x", 8, -6, 0, (-3,), "security_hall", ("Охрана — вход из холла",))
    wall("z", 0, 0, 8)
    # Reception is a staffed counter open to the hall, rather than a closed office.
    wall("x", 0, 5, 18)
    wall("z", 5, 0, 3.5)
    wall("z", 18, 0, 2)

    # Four waiting benches and small tables line the south wall, as in the plan.
    for x in (-16.8, -9.8, 9.4, 16.3):
        with props.against_wall("z", 13.88, inward=-1):
            props.sofa(x, 12.6, 3.0)
    props.table(-13.3, 12.1, 0.75, 0.7)
    props.table(12.8, 12.1, 0.75, 0.7)
    with props.against_wall("z", -2.14, inward=-1):
        props.sofa(-10, -2.9, 3.0)
    # The east bench follows reception's north wall and faces the corridor.
    with props.against_wall("z", -0.12, inward=-1):
        props.sofa(13.2, -2.9, 3.0)
    props.table(2.5, 6.5, 0.75, 0.75)
    # U-shaped reception with chamfered corners and a staff entrance on the east.
    with props.authored_group("reception", 11.6, 6.2, extra_boxes=boxes):
        for position, size, yaw in (
            ((11.6, 0.7375, 6.2), (9.6, 1.475, 0.6), 0),
            ((6.1, 0.7375, 5.35), (0.6, 1.475, 2.4), 35),
            ((5.5, 0.7375, 3.4), (0.6, 1.475, 2.2), 0),
            ((17.1, 0.7375, 5.35), (0.6, 1.475, 2.4), -35),
            ((17.8, 0.7375, 3.9), (0.6, 1.475, 0.9), 0),
        ):
            box(position, size, "wood", yaw=yaw)
            box((position[0], 1.5, position[2]), (size[0] + 0.12, 0.12, size[2] + 0.12), "wood", yaw=yaw)
        for x in (9.2, 13.6):
            props.desk_details(x, 6.2, height=1.56)
    props.chair(11.5, 4.8, 180)
    with props.against_wall("z", 0.12):
        props.cabinet(7.0, 0.8, 1.8, 1.7, yaw=180)
        props.linen_shelf(11, 0.8, 2.0)
        props.cabinet(16, 0.9, 1.4, 2.1, yaw=180)
    props.table(8.1, 2.0, 1.2, 0.7, 0.8)
    props.plant(6.3, 3.2)
    props.sign(11.5, 0.16, "Регистрация — обращайтесь к стойке", yaw=180, width=1.8)
    # Keep both security door swings free of the desk and filing cabinets.
    with props.authored_group("security_desk", -3, 4.9, extra_boxes=boxes):
        desk(-3, 4.9, 3.2, 0.9)
        props.desk_details(-3, 4.9)
    definitions.extend((
        {"id": "security_archive", "type": "story_prop", "name": "Архив камер", "action": "Изучить записи камер",
         "position": (-2.75, 1.22, 4.923), "size": (0.52, 0.35, 0.015),
         "color": (0.14, 0.24, 0.19), "emission": (0.035, 0.07, 0.045)},
        {"id": "incident_report", "type": "story_document", "name": "Отчёт о происшествии",
         "position": (-3.55, 1.06, 4.86), "size": (0.37, 0.035, 0.29),
         "selection_size": (0.5, 0.15, 0.38), "initial": "unavailable"},
    ))
    props.chair(-3, 3.65)
    with props.against_wall("z", 0.12):
        props.cabinet(-0.9, 1.1, 1.2, 2.0, yaw=180)
    with props.against_wall("x", -5.86):
        props.cabinet(-5.3, 3.2, 1.6, 1.7, yaw=-90)
    props.sign(-1.4, 0.16, "Охрана", yaw=180)
    props.sign(-1.4, 8.16, "Охрана", yaw=180)

    for x, z in ((-19.2, -2.9), (-5.0, -2.8), (7.5, -2.8), (20.45, -1.7),
                 (-19.5, 10.4), (-6.0, 12.6), (6.0, 12.6), (20.45, 8.4)):
        props.plant(x, z)

    for i, x in enumerate(OFFICE_DOORS):
        # Светлая плитка и разная обстановка отличают кабинеты друг от друга.
        props.part(x, -10, (0, 0.006, 0), (6.65, 0.012, 7.65),
                   "ward_floor" if i in (4, 5) else "office_floor" if i == 0
                   else "storage_floor" if i == 3 else "clinical_floor", detail=True)
        if i in (4, 5):
            for side in (-1, 1):
                bed(x + side * 1.45, -10.6)
                props.cabinet(x + side * 2.45, -12.4, 0.45, 0.65)
            props.privacy_screen(x, -12.0, yaw=90, width=2.2)
            props.table(x + 2.55, -6.55, 0.45, 0.45, 0.72)
        if i == 0:
            with props.against_wall("z", -13.88, extra_boxes=boxes):
                with props.authored_group("office_desk", -19, -10.6, extra_boxes=boxes):
                    desk(-19, -10.6, 2.2)
                    with props.rotated_group(-19, -10.6, 180):
                        props.desk_details(-19, -10.6)
            props.chair(-19, -12.0, 180)
            props.chair(-17.4, -12.0, 180)
            with props.against_wall("z", -13.88):
                props.cabinet(-14.8, -12.7, 1.2, yaw=180, medical=False)
            props.plant(-14.7, -6.8)
        if i == 1:
            bed(x, -10.6)
            props.privacy_screen(x + 1.9, -12.0, yaw=90)
            with props.against_wall("x", -13.86):
                props.cart(x - 2.0, -11.5)
            with props.against_wall("z", -13.88):
                props.sink(x + 1.8, -12.8, yaw=180)
            with props.against_wall("z", -6.14, inward=-1):
                props.cabinet(x + 2.2, -7.4, 1.2)
            props.iv_stand(x - 1.05, -12.2)
            # Adjustable examination lamp, with its shade over the couch.
            with props.authored_group("examination_lamp", x, -12.38):
                props.part(x, -12.38, (-1.5, 0.06, -0.3), (0.65, 0.08, 0.5), "rust")
                props.part(x, -12.38, (-1.5, 1.2, -0.3), (0.06, 2.3, 0.06), "rust")
                props.part(x, -12.38, (-0.8, 2.3, -0.3), (1.4, 0.055, 0.055), "rust", detail=True)
                props.part(x, -12.38, (-0.1, 2.25, -0.3), (0.6, 0.1, 0.55), "rust", detail=True)
        if i == 2:
            bed(x - 1.0, -10.6)
            props.privacy_screen(x - 2.4, -12.0, yaw=90)
            with props.against_wall("z", -13.88, extra_boxes=boxes):
                with props.authored_group("exam_desk", x + 1.4, -11.9, extra_boxes=boxes):
                    desk(x + 1.4, -11.9, 1.8)
                    with props.rotated_group(x + 1.4, -11.9, 180):
                        props.desk_details(x + 1.4, -11.9)
            props.chair(x + 1.4, -12.0, 180)
            with props.against_wall("z", -6.14, inward=-1):
                props.cabinet(x + 1.9, -8.0, 1.1)
            with props.against_wall("x", -0.14, inward=-1):
                props.cart(x - 0.9, -10.0)
        if i == 3:
            with props.against_wall("z", -13.88):
                props.linen_shelf(x - 1.6, -12.7, 2.7)
                props.cabinet(x + 1.9, -12.5, 1.2, 2.3, yaw=180)
            props.cart(x + 1.8, -8.0)
            for y in (0.38, 1.12):
                props.part(6.4, -6.6, (0, y, 0), (0.75, 0.72, 0.75),
                           "wood", (0.37, 0.31, 0.2))
        props.radiator(x, -13.65)
        plaque = Box((x + 1.35, 1.7, -5.84), (0.75, 0.28, 0.035), material="rust",
                     color=(0.27, 0.36, 0.31),
                     interaction=Interaction(ROOM_NAMES[i], ROOM_NAMES[i] + "."))
        boxes.append(plaque)
        lamp(x, -10)
    for x in (-17, -9, -1, 7, 16):
        lamp(x, -3.5)
    for x, z in ((-15, 11.5), (-5, 11.5), (5, 11.5), (15, 11.5), (-3, 4), (11, 3)):
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
    palette = hospital_palette(peaceful)
    for definition in definitions:
        if not definition.get("elevator"):
            definition["panel_material"] = "door_panel"
            definition["frame_material"] = "wall_tile_frame"
            definition["handle_material"] = "brushed_metal"
    if peaceful:
        # The building is shared; story access to the upper floors stays gated.
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
    surgical_floor = build_surgical_floor(peaceful=peaceful)
    patient_floor = build_patient_floor(peaceful=peaceful)
    result = assemble_storeys(level, tuple(boxes) + tuple(props.boxes),
                            tuple(decorations) + tuple(props.decorations), definitions, lights,
                            stair, count=floor_count, material_map=palette,
                            ceiling_material="ceiling_acoustic_panels" if peaceful else "ceiling_mold",
                            surgical_floor=surgical_floor, patient_floor=patient_floor)
    if surgical_floor is not None:
        result = replace(
            result,
            floor_size=PATIENT_FLOOR_SIZE,
            floor_labels=("1", "2 — хирургия", "3 — пациентское отделение"),
            floor_hints=("", "Хирургическое отделение", "Пациентское отделение"),
        )
    if not peaceful:
        from game.levels.stair_blood import stair_blood
        blood = stair_blood(stair)
        result = replace(result, decorations=blood + result.decorations,
                         stair_blood_targets=tuple((box.position[0], box.position[1] + 0.015, box.position[2])
                                                   for box in blood if box.position[1] < 0.02 and box.size[0] >= 1))
    if any(obj.entity is not None and hasattr(obj.entity, "following") for obj in result.objects):
        from game.levels.hospital_navigation import build_hospital_navigation
        storey_definitions = None
        floor_sizes = None
        if surgical_floor is not None:
            floor_definitions = tuple(surgical_floor[3])
            patient_definitions = tuple(patient_floor[3])
            storey_definitions = (tuple(definitions), floor_definitions, patient_definitions)
            floor_sizes = ((43.0, 29.0), SURGERY_FLOOR_SIZE, PATIENT_FLOOR_SIZE)
        result = replace(
            result,
            navigation=build_hospital_navigation(
                result, stair, definitions, storey_definitions=storey_definitions,
                floor_sizes=floor_sizes,
            ),
        )
    return result
