"""Second-floor hospital wing laid out to match the supplied overhead reference."""

from engine.scene.box import Box
from engine.scene.lighting import PointLight
from game.levels.hospital_props import HospitalProps


SURGERY_FLOOR_SIZE = (60.0, 48.0)
SURGERY_WALL_HEIGHT = 4.56


def build_surgical_floor(*, peaceful=False):
    boxes = []
    definitions = []
    lights = []
    props = HospitalProps()

    def wall(axis, fixed, start, end):
        if end <= start:
            return
        for low, high, material in (
            (0, 1.35, "wall_tile_clinical"),
            (1.35, SURGERY_WALL_HEIGHT, "plaster"),
        ):
            center = ((start + end) / 2, (low + high) / 2, fixed)
            size = (end - start, high - low, 0.24)
            if axis == "z":
                center = (fixed, center[1], center[0])
                size = (0.24, size[1], end - start)
            boxes.append(Box(center, size, material=material))
        center = ((start + end) / 2, 0.075, fixed)
        size = (end - start, 0.15, 0.28)
        if axis == "z":
            center, size = (fixed, 0.075, center[0]), (0.28, 0.15, end - start)
        boxes.append(Box(center, size, material="skirting"))

    def partition(axis, fixed, start, end, doors=()):
        cursor = start
        for center, object_id, name in sorted(doors):
            wall(axis, fixed, cursor, center - 0.95)
            position = (center, 0, fixed) if axis == "x" else (fixed, 0, center)
            definitions.append({
                "id": object_id,
                "type": "door",
                "position": position,
                "name": name,
                "width": 1.65,
                "height": 2.65,
                "opening_width": 1.9,
                "wall_height": SURGERY_WALL_HEIGHT,
                "axis": axis,
                "panel_material": "door_panel",
                "frame_material": "wall_tile_frame",
                "handle_material": "brushed_metal",
                "open_seconds": 0.6,
            })
            cursor = center + 0.95
        wall(axis, fixed, cursor, end)

    def lamp(x, z):
        color = (1.0, 0.96, 0.87) if peaceful else (0.58, 0.76, 0.69)
        lights.append(PointLight((x, 3.95, z), color, 3.0 if peaceful else 3.6, 9.0))
        props.decorations.append(Box((x, 4.28, z), (1.5, 0.08, 0.36),
                                     material="rust", color=(0.2, 0.24, 0.22)))
        props.decorations.append(Box((x, 4.23, z), (1.24, 0.025, 0.2),
                                     emission=(0.35, 0.54, 0.43)))

    def operating_table(x, z):
        boxes.extend((
            Box((x, 0.43, z), (0.18, 0.66, 0.18), material="rust"),
            Box((x, 0.10, z), (0.8, 0.20, 1.9), material="rust"),
            Box((x, 0.78, z), (1.0, 0.16, 2.25), material="rust",
                color=(0.32, 0.38, 0.34)),
            Box((x, 0.91, z), (0.9, 0.12, 1.95), material="bed_blanket",
                color=(0.53, 0.57, 0.51)),
            Box((x, 3.695, z), (0.16, 1.69, 0.16), material="rust"),
            Box((x, 2.88, z), (1.35, 0.12, 0.42), material="rust",
                color=(0.2, 0.24, 0.21)),
            Box((x, 2.8, z), (1.1, 0.035, 0.28), material="rust",
                emission=(0.5, 0.58, 0.45)),
        ))

    def bed(x, z):
        boxes.extend((
            Box((x, 0.42, z), (1.18, 0.2, 2.15), material="medical_enamel",
                color=(0.31, 0.36, 0.32)),
            Box((x, 0.58, z), (1.08, 0.15, 1.96), material="bed_linen",
                color=(0.68, 0.67, 0.58)),
            Box((x, 0.26, z - 0.75), (1.22, 0.52, 0.08), material="medical_enamel"),
        ))
        for dx in (-0.43, 0.43):
            for dz in (-0.75, 0.75):
                boxes.append(Box((x + dx, 0.16, z + dz), (0.08, 0.32, 0.08), material="rust"))
        props.bed_details(x, z)

    # Close all four sides of the enlarged second-floor footprint.
    partition("x", -24, -30, 30)
    partition("x", 24, -30, 30)
    partition("z", -30, -24, 24)
    partition("z", 30, -24, 24)

    # The seven small rooms across the top edge are entered from one corridor.
    partition("x", -22, -28, 28)
    partition("x", -10, -28, 28, (
        (-24, "surgery_xray", "Рентген"),
        (-16, "surgery_preop", "Предоперационная"),
        (-8, "surgery_or_1", "Операционная №1"),
        (0, "surgery_surgeon", "Кабинет хирурга"),
        (8, "surgery_sterilization", "Стерилизация"),
        (16, "surgery_or_2", "Операционная №2"),
        (24, "surgery_pharmacy", "Склад медикаментов"),
    ))
    for x in (-20, -12, -4, 4, 12, 20):
        partition("z", x, -22, -10)
    for x in (-28, 28):
        partition("z", x, -22, -10)

    # A broad cross-corridor connects the stair lobby to the north rooms and wards.
    partition("x", -6, -6, 28, (
        (0, "surgery_nurses_entry", "Пост медсестёр"),
        (12, "surgery_recovery", "Послеоперационная"),
        (22, "surgery_staff_entry", "Комната персонала"),
    ))

    # The stair lobby remains open around the existing spiral stair and its bridge.
    wall("z", -6, -6, 3)
    wall("z", -6, 12, 22)

    # Nurse station, six-bed ward, and a small shared room line the inner corridor.
    for start, end in ((-5, -1), (1, 11), (13, 21), (23, 28)):
        wall("x", -2, start, end)
    for start, end in ((-5, 9), (11, 28)):
        wall("x", 8, start, end)
    partition("z", -5, -2, 8, ((4, "surgery_nurses", "Пост медсестёр"),))
    for x in (4, 16):
        wall("z", x, -2, 0)
        wall("z", x, 2, 8)
    partition("z", 28, -2, 8)

    # Quiet room and electrical room occupy the bottom-right part of the plan.
    partition("x", 14, -5, 28, (
        (4, "surgery_staff_room", "Комната персонала"),
        (21, "surgery_electrical", "Электрощитовая"),
    ))
    partition("x", 22, 14, 28)
    partition("x", 22, -5, 14)
    partition("z", 14, 14, 22, ((18, "surgery_electrical_door", "Электрощитовая"),))
    partition("z", 28, 14, 22)
    partition("z", -5, 14, 22, ((18, "surgery_staff", "Комната персонала"),))
    # This door opens into the staff room, away from the parallel lobby wall.
    next(data for data in definitions if data["id"] == "surgery_staff")["open_angle"] = 90

    # Equipment is kept clear of the stair opening and the main walking routes.
    with props.against_wall("z", -21.88):
        props.cabinet(-26.7, -17, 1.1, 1.8, yaw=180)
        props.cart(-23, -17)
    with props.against_wall("z", -21.88):
        props.table(-16, -16, 2.2, 1.0, 0.85)
    operating_table(-8, -16)
    with props.against_wall("x", -3.88):
        props.cabinet(-2, -19, 1.2, 1.9, yaw=-90)
    with props.against_wall("z", -21.88):
        props.table(7, -16, 2.0, 0.9, 0.85)
        props.cabinet(10.6, -16, 1.3, 2.0, yaw=180)
    operating_table(16, -16)
    props.cart(19, -16)
    with props.against_wall("x", 27.86, inward=-1):
        for z in (-19.8, -18.4):
            props.cabinet(26, z, 0.9, 1.8, yaw=90)
    with props.against_wall("x", 20.14):
        props.cart(24, -13)
    with props.against_wall("z", -21.88):
        props.linen_shelf(23.7, -20.8, 3.6)
        props.table(0.8, -20.8, 2.4, 0.9, 0.85)
        with props.rotated_group(0.8, -20.8, 180):
            props.desk_details(0.8, -20.8, height=0.85)
        props.sink(5.3, -20.8, yaw=180)
    props.chair(0.8, -20.0, 180)
    for x in (-10.2, 13.8):
        with props.against_wall("z", -21.88):
            props.sink(x, -20.8, yaw=180)
        props.monitor(x, -16.5)
        props.iv_stand(x + 1.2, -17.5)
    with props.against_wall("z", -21.88):
        props.cabinet(-5.3, -19.7, 1.1, 1.8, yaw=180)
        props.cabinet(18.7, -19.7, 1.1, 1.8, yaw=180)

    # L-shaped nurse counter and a six-bed recovery ward.
    with props.against_wall("z", 7.86, inward=-1, extra_boxes=boxes):
        boxes.extend((
            Box((-2.0, 0.75, 4.8), (0.45, 1.5, 5.2), material="wood"),
            Box((0.2, 0.75, 7.15), (4.85, 1.5, 0.45), material="wood"),
            Box((-1.85, 1.55, 4.8), (0.6, 0.12, 5.35), material="wood"),
            Box((0.2, 1.55, 6.85), (4.95, 0.12, 0.6), material="wood"),
        ))
    props.chair(0, 3.5, yaw=90)
    for surface, inward, x in ((4.14, 1, 4.81), (15.86, -1, 15.19)):
        for z in (2.4, 4.6, 6.8):
            with props.against_wall("x", surface, inward=inward, extra_boxes=boxes):
                bed(x, z)
            props.cart(x + inward * 1.05, z)
    for x in (18.5, 25.5):
        with props.against_wall("z", -1.86):
            props.sofa(x, 2.0, width=2.5, yaw=180)
    props.table(22, 6, 2.2, 1.0, 0.75)
    props.chair(21, 7.4)
    props.chair(23, 7.4, yaw=180)

    # Waiting seats and a quiet-room table echo the reference image.
    with props.against_wall("x", -29.86):
        props.sofa(-24, -3, width=2.8, yaw=-90)
        props.sofa(-24, 18, width=2.8, yaw=-90)
    with props.against_wall("z", 21.86, inward=-1):
        props.sofa(1, 18, width=2.8)
        props.sofa(9, 18, width=2.8)
    props.table(5, 18, 2.2, 1.0, 0.72)
    props.chair(4, 16.8, yaw=180)
    props.chair(6, 16.8, yaw=180)
    for x, z in ((-27, -7), (-27, 11), (-8, 20), (12, 11), (27, 10)):
        props.plant(x, z, small=True)

    # Electrical cabinets and exposed conduit are grouped in the lower-right room.
    for x in (17, 20, 23):
        boxes.append(Box((x, 1.45, 21.7), (1.25, 2.45, 0.28), material="rust",
                         color=(0.34, 0.37, 0.32)))
        boxes.append(Box((x, 1.55, 21.52), (0.82, 1.58, 0.06), material="rust",
                         color=(0.48, 0.49, 0.39)))
        for z in (21.47,):
            boxes.append(Box((x, 1.65, z), (0.12, 0.12, 0.035), material="rust",
                             emission=(0.42, 0.29, 0.12)))
    for y in (2.7, 3.0):
        boxes.append(Box((27.75, y, 19.4), (0.12, 0.12, 4.2), material="rust"))
        boxes.append(Box((25.8, y, 21.75), (4.0, 0.12, 0.12), material="rust"))

    for x, z in ((-24, -16), (-16, -16), (-8, -16), (0, -16),
                 (8, -16), (16, -16), (24, -16), (-18, -8),
                 (-1, 4), (7, 4), (21, 4), (-24, 16), (4, 18), (21, 18)):
        lamp(x, z)

    for data in definitions:
        x, _, z = data["position"]
        if data["axis"] == "x":
            props.sign(x + 1.35, z + 0.16, data["name"], yaw=180)
        else:
            props.sign(x + 0.16, z + 1.35, data["name"], yaw=-90)

    # Ceiling skins are generated from the actual slabs in hospital_storeys.
    return tuple(boxes) + tuple(props.boxes), tuple(props.decorations), tuple(lights), tuple(definitions)
