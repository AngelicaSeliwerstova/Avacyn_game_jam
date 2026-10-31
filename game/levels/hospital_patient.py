"""Third-floor patient ward with small rooms and a shared ward corridor."""

from engine.scene.box import Box
from engine.scene.lighting import PointLight
from game.levels.hospital_props import HospitalProps


PATIENT_FLOOR_SIZE = (60.0, 48.0)
PATIENT_WALL_HEIGHT = 4.56


def build_patient_floor(*, peaceful=False):
    boxes = []
    definitions = []
    lights = []
    props = HospitalProps()

    def wall(axis, fixed, start, end):
        if end <= start:
            return
        for low, high, material in (
            (0, 1.35, "wall_tile_ward"),
            (1.35, PATIENT_WALL_HEIGHT, "plaster"),
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
                "wall_height": PATIENT_WALL_HEIGHT,
                "axis": axis,
                "panel_material": "door_panel",
                "frame_material": "wall_tile_frame",
                "handle_material": "brushed_metal",
                "open_seconds": 0.6,
            })
            cursor = center + 0.95
        wall(axis, fixed, cursor, end)

    def lamp(x, z):
        color = (1.0, 0.96, 0.87) if peaceful else (0.64, 0.72, 0.59)
        lights.append(PointLight((x, 3.95, z), color, 2.8 if peaceful else 3.2, 8.0))
        props.decorations.append(Box((x, 4.28, z), (1.35, 0.08, 0.32),
                                     material="rust", color=(0.2, 0.22, 0.18)))
        props.decorations.append(Box((x, 4.23, z), (1.1, 0.025, 0.18),
                                     emission=(0.39, 0.43, 0.3)))

    def bed(x, z, yaw=0):
        with props.rotated_group(x, z, yaw, extra_boxes=boxes):
            add_bed(x, z)

    def add_bed(x, z):
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

    # Close all four sides of the third-floor footprint.
    partition("x", -24, -30, 30)
    partition("x", 24, -30, 30)
    partition("z", -30, -24, 24)
    partition("z", 30, -24, 24)

    # Eight compact patient rooms form the north side of the floor.
    partition("x", -22, -28, 28)
    partition("x", -10, -28, 28, tuple(
        (center, f"patient_room_{index}", f"Палата {index + 1:02}")
        for index, center in enumerate((-24.5, -17.5, -10.5, -3.5, 3.5, 10.5, 17.5, 24.5))
    ))
    # Keep the hinge away from the nurse-office wall meeting this doorway.
    next(data for data in definitions if data["id"] == "patient_room_3")["hinge_side"] = "right"
    for x in (-21, -14, -7, 0, 7, 14, 21):
        partition("z", x, -22, -10)
    for x in (-28, 28):
        partition("z", x, -22, -10)

    # The long hall stays open in front of the north rooms and around the stair.
    # Compact rooms are placed to either side of the clear east-west route.
    partition("z", -4, -10, -3, ((-7, "patient_nurse_room", "Кабинет дежурной медсестры"),))
    partition("x", -4, -10, -3, ((-7, "patient_nurse_inner", "Пост медсестры"),))
    partition("x", 8, 16, 28)
    partition("z", 16, -4, 8, ((1, "patient_east_entry", "Палата"),))
    partition("x", -4, 16, 28)
    partition("z", 28, -4, 8)

    # Three southern wards face the cross-corridor; the center route to the stair
    # landing remains unobstructed.
    partition("x", 14, -10, -1, ((-6, "patient_south_west", "Палата"),))
    partition("x", 14, 5, 15, ((10, "patient_south_center", "Палата"),))
    partition("x", 14, 18, 28, ((23, "patient_south_east", "Палата"),))
    partition("z", -10, 14, 22)
    partition("z", -1, 14, 22)
    partition("z", 5, 14, 22)
    partition("z", 15, 14, 22)
    partition("z", 18, 14, 22)
    partition("z", 28, 14, 22)
    for start, end in ((-10, -1), (5, 15), (18, 28)):
        partition("x", 22, start, end)

    # Bed, locker, and chair in each small room along the north wall.
    for center in (-24.5, -17.5, -10.5, -3.5, 3.5, 10.5, 17.5, 24.5):
        x = center - 2.67
        with props.against_wall("x", center - 3.38, gap=0.1, extra_boxes=boxes):
            with props.against_wall("z", -21.88, gap=0.08, extra_boxes=boxes):
                bed(x, -17)
        props.cabinet(x + 1.05, -20.65, 0.45, 0.65)
        props.iv_stand(x + 1.9, -20.65)
        with props.against_wall("z", -21.88):
            props.cabinet(center + 2.95, -19, 0.72, 1.55, yaw=180)
        with props.against_wall("x", center + 3.38, inward=-1):
            props.chair(center + 2.95, -18.2, yaw=90)

    # Staff counter near the stair landing; chairs and desk face the hallway.
    with props.against_wall("z", -9.86):
        props.table(-7.3, -8.5, 3.2, 1.0, 0.95)
        with props.rotated_group(-7.3, -8.5, 180):
            props.desk_details(-7.3, -8.5, height=0.95)
    props.chair(-7.3, -8.0, yaw=180)
    with props.against_wall("x", -4.14, inward=-1):
        props.cabinet(-6.4, -5.5, 0.9, 1.7, yaw=90)
    props.plant(-2.2, 5.8, small=True)

    # A quiet ward on the east side and small utility equipment.
    for x in (20, 24):
        for surface, inward, yaw in ((-3.88, 1, 0), (7.88, -1, 180)):
            with props.against_wall("z", surface, inward=inward, gap=0.08, extra_boxes=boxes):
                bed(x, 0, yaw=yaw)
                props.cart(x + 1.1, 0)
                props.monitor(x - 1.15, 0, yaw=yaw)
    with props.against_wall("x", 27.88, inward=-1):
        props.cabinet(26.5, 4.5, 0.9, 1.8, yaw=90)
    props.table(19, 9.5, 2.0, 0.85, 0.75)
    props.chair(18, 10.8, yaw=180)
    props.chair(20, 10.8, yaw=180)

    # Southern rooms get varied patient beds, cabinets, and a small linen store.
    for x, z in ((-7, 17), (-4, 17), (7.5, 17), (12, 17), (20, 17), (25, 17)):
        with props.against_wall("z", 21.88, inward=-1, gap=0.08, extra_boxes=boxes):
            bed(x, z, yaw=180)
        props.iv_stand(x - 0.95, 20.4)
    for x in (-9, -2, 6, 14, 19, 27):
        with props.against_wall("z", 14.14):
            props.cabinet(x, 20, 0.9, 1.8, yaw=180)
    props.cart(9, 21.3)
    props.table(-4.2, 15, 1.8, 0.75, 0.72)
    props.chair(-4.2, 16.3)
    props.sofa(24, 10.5, width=2.5)
    props.plant(28, 10, small=True)
    with props.against_wall("x", -29.88):
        props.linen_shelf(-26.5, 17.5, 2.4, yaw=-90)
        props.linen_shelf(-26.5, 20.1, 2.4, yaw=-90)

    for data in definitions:
        x, _, z = data["position"]
        if data["axis"] == "x":
            props.sign(x + 1.35, z + 0.16, data["name"], yaw=180)
        else:
            props.sign(x + 0.16, z + 1.35, data["name"], yaw=-90)

    for x, z in ((-24, -16), (-10, -16), (4, -16), (18, -16), (26, -16),
                 (-8, 1), (12, 1), (24, 3), (-5, 18), (10, 18), (24, 18)):
        lamp(x, z)

    # Ceiling skins are generated from the actual slabs in hospital_storeys.
    return tuple(boxes) + tuple(props.boxes), tuple(props.decorations), tuple(lights), tuple(definitions)
