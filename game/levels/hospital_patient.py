"""Third-floor patient ward with small rooms and a shared ward corridor."""

from engine.scene.box import Box
from game.levels import furniture
from engine.scene.lighting import PointLight
from game.levels.hospital_props import HospitalProps
from game.levels.room_signs import PATIENT_SIGNS, PATIENT_SIGN_WIDTH, PATIENT_SIGN_HEIGHT
from engine.scene.interaction import Interaction


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
        furniture.bed(boxes, props, x, z)

    # Close all four sides of the third-floor footprint.
    partition("x", -24, -30, 30)
    partition("x", 24, -30, 30)
    partition("z", -30, -24, 24)
    partition("z", 30, -24, 24)

    # Eight compact patient rooms form the north side of the floor.
    # Rooms share the exterior walls instead of leaving perimeter alleys.
    partition("x", -10, -30, 30, tuple(
        (center, f"patient_room_{index}", f"Палата {index + 1:02}")
        for index, center in enumerate((-24.5, -17.5, -12, -2, 3.5, 10.5, 17.5, 24.5))
    ))
    for x in (-21, -14, -7, 0, 7, 14, 21):
        partition("z", x, -24, -10)

    # The long hall stays open in front of the north rooms and around the stair.
    # Compact rooms are placed to either side of the clear east-west route.
    partition("z", -10, -10, -4)
    # One entrance faces the hall; the side walls meet solid north-wall sections.
    # The adjacent ward doors sit beyond the office corners, rather than across them.
    partition("z", -4, -10, -4)
    partition("x", -4, -10, -4, ((-7, "patient_nurse_room", "Пост медсестры"),))
    partition("x", 8, 16, 30)
    partition("z", 16, -4, 8, ((1, "patient_east_entry", "Палата"),))
    partition("x", -4, 16, 30)

    # Three southern wards face the cross-corridor; the center route to the stair
    # landing remains unobstructed.
    # A continuous row shares partitions and the south/west/east envelope.
    partition("x", 14, -30, 2, ((-6, "patient_south_west", "Палата"),))
    partition("x", 14, 2, 16, ((10, "patient_south_center", "Палата"),))
    partition("x", 14, 16, 30, ((23, "patient_south_east", "Палата"),))
    for x in (2, 16):
        partition("z", x, 14, 24)

    # Bed, locker, and chair in each small room along the north wall.
    for center in (-24.5, -17.5, -10.5, -3.5, 3.5, 10.5, 17.5, 24.5):
        x = center - 2.67
        left_surface = -29.86 if center == -24.5 else center - 3.38
        with props.against_wall("x", left_surface, gap=0.1, extra_boxes=boxes):
            with props.against_wall("z", -23.86, gap=0.08, extra_boxes=boxes):
                bed(x, -17)
        props.cabinet(x + 1.05, -20.65, 0.45, 0.65)
        props.iv_stand(x + 1.9, -20.65)
        with props.against_wall("z", -23.86):
            props.cabinet(center + 2.95, -19, 0.72, 1.55, yaw=180)
        right_surface = 29.86 if center == 24.5 else center + 3.38
        with props.against_wall("x", right_surface, inward=-1):
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
    with props.against_wall("x", 29.86, inward=-1):
        props.cabinet(26.5, 4.5, 0.9, 1.8, yaw=90)
    props.table(19, 9.5, 2.0, 0.85, 0.75)
    props.chair(18, 10.8, yaw=180)
    props.chair(20, 10.8, yaw=180)

    # Southern rooms get varied patient beds, cabinets, and a small linen store.
    for x, z in ((-7, 17), (-4, 17), (7.5, 17), (12, 17), (20, 17), (25, 17)):
        with props.against_wall("z", 23.86, inward=-1, gap=0.08, extra_boxes=boxes):
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
        text = PATIENT_SIGNS[data["id"]]
        data["name"] = text.replace("\n", " ").capitalize()
        if data["axis"] == "x":
            # North rooms and the nurse office face south; southern wards face north.
            side = -1 if z == 14 else 1
            position = (x + 1.9, 1.75, z + side * 0.16)
            yaw = 180 if side == -1 else 0
        else:
            position = (x - 0.16, 1.75, z + 1.9)
            yaw = -90
        props.decorations.append(Box(position, (PATIENT_SIGN_WIDTH, PATIENT_SIGN_HEIGHT, 0.035),
                                     material=f"sign_{data['id']}", local_texture=True, yaw_degrees=yaw,
                                     interaction=Interaction(data["name"], data["name"], "Прочитать")))

    for x, z in ((-24, -16), (-10, -16), (4, -16), (18, -16), (26, -16),
                 (-8, 1), (12, 1), (24, 3), (-5, 18), (10, 18), (24, 18)):
        lamp(x, z)

    # Ceiling skins are generated from the actual slabs in hospital_storeys.
    return tuple(boxes) + tuple(props.boxes), tuple(props.decorations), tuple(lights), tuple(definitions)
