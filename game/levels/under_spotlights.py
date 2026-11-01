"""The empty second-floor cradle room and the damaged stair handrail."""

from engine.scene.box import Box
from engine.scene.camera import FixedCameraZone
from game.levels.cameras import camera_model_boxes


NURSERY_DOOR = "f2_surgery_preop"
NURSERY_KEY = "second_floor_key"
NURSERY_CRADLE = "f2_nursery_cradle"
CRADLE_TARGET = (-16.0, 5.6, -20.5)
MEMORY_CAMERA = (-13.2, 6.65, -17.8)


def add_nursery(props, boxes, definitions):
    x, z = -16.0, -20.5

    def part(dx, y, dz, size, material="wood", color=None, *, solid=False):
        box = Box((x + dx, y, z + dz), size, material=material, color=color)
        (boxes if solid else props.decorations).append(box)

    # A hollow wooden cradle: mattress, end panels, bars and two rocking runners.
    part(0, 0.67, 0, (1.14, 0.12, 1.75), solid=True)
    part(0, 0.76, 0, (1.02, 0.10, 1.58), "linen_worn")
    for side in (-1, 1):
        part(side * 0.58, 0.40, 0, (0.10, 0.54, 1.62), solid=True)
        part(side * 0.58, 0.13, 0, (0.17, 0.13, 2.00))
        part(side * 0.58, 1.07, 0, (0.08, 0.08, 1.80))
        for offset in (-0.68, -0.42, -0.16, 0.10, 0.36, 0.62):
            part(side * 0.58, 0.90, offset, (0.04, 0.32, 0.04))
        part(0, 0.91, side * 0.86, (1.20, 0.40, 0.08), solid=True)
    # A mobile remains suspended over the empty mattress.
    part(0.70, 1.58, 0.46, (0.035, 1.54, 0.035), "rust")
    part(0.28, 2.34, 0.46, (0.87, 0.035, 0.035), "rust")
    part(0, 2.17, 0.22, (0.025, 0.34, 0.025), "rust")
    part(0, 1.99, 0.22, (0.85, 0.025, 0.025), "rust")
    part(0, 1.99, 0.22, (0.025, 0.025, 0.72), "rust")
    for dx, dz, color in ((-0.40, 0.22, (0.52, 0.17, 0.12)), (0.40, 0.22, (0.52, 0.44, 0.18)),
                          (0, -0.10, (0.18, 0.35, 0.41)), (0, 0.54, (0.29, 0.39, 0.20))):
        part(dx, 1.83, dz, (0.018, 0.31, 0.018), "rust")
        part(dx, 1.65, dz, (0.16, 0.13, 0.10), color=color)
    props.cabinet(-18.7, -22.7, 1.1, 1.8, medical=False)
    for tx, tz, color in ((-13.5, -19, (0.50, 0.23, 0.16)), (-17.9, -18.9, (0.23, 0.38, 0.40)),
                           (-14, -22.8, (0.48, 0.40, 0.17))):
        props.decorations.extend((Box((tx, 0.18, tz), (0.3, 0.35, 0.28), color=color),
                                  Box((tx, 0.43, tz), (0.22, 0.22, 0.22), color=color)))
    for px in (-17.0, -15.2):
        props.decorations.append(Box((px, 1.65, -23.83), (0.85, 0.64, 0.03),
                                     material="story_drawing", local_texture=True))
    for position in ((-19.4, 3.3, -23.4), (-12.7, 3.15, -23.3), (-19.4, 3.3, -12), (-12.7, 3.3, -12)):
        camera = FixedCameraZone((-19.8, -0.1, -23.8), (-12.2, 4.4, -10.2), position, (x, 0.8, z))
        props.decorations.extend(camera_model_boxes(camera, True, aim_pitch=True))
    definitions.append({"id": "nursery_cradle", "type": "story_prop", "name": "Пустая детская люлька",
                        "action": "Осмотреть люльку", "position": (x, 0.82, z), "size": (1.0, 0.05, 1.50),
                        "selection_size": (1.30, 0.65, 1.90),
                        "color": (0.59, 0.57, 0.46)})


def damaged_stair_rail(stair):
    point = stair.point(-15, 2.95, 1.45)
    x, y, z = point
    return (Box((x + 0.19, y - 0.38, z), (0.09, 0.9, 0.09), material="rust"),
            Box((x + 0.08, y, z), (0.24, 0.025, 0.025), material="rust", yaw_degrees=-15),
            Box((x - 0.01, y + 0.003, z), (0.05, 0.03, 0.034), color=(0.43, 0.018, 0.012)))
