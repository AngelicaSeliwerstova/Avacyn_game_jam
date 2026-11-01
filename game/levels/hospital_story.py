"""Physical Act 1 props; narrative and sound rules live in resources/story."""
from engine.scene.box import Box
from engine.scene.camera import FixedCameraZone
from game.levels.cameras import camera_model_boxes

CHILD_BED_TARGET = (22.9, 0.7, -21.0)
CHILD_CAMERAS = ((21.3, 3.25, -23.1), (25.2, 3.45, -23.5), (29.5, 3.1, -22),
                 (29.5, 3.3, -18.4), (23.1, 3.6, -17.5), (26.5, 4.0, -20.3))
STORY_SURFACE_SIZES = {"story_tv_static_a": (1.4, 0.80), "story_tv_static_b": (1.4, 0.80),
                       "story_tv_memory": (1.4, 0.80), "story_drawing": (0.85, 0.64),
                       "story_clock": (0.72, 0.72)}


def add_patient_story(props, boxes, definitions):
    def part(position, size, color):
        props.decorations.append(Box(position, size, color=color))

    def story(object_id, name, position, size, material=None, **extra):
        definitions.append({"id": object_id, "type": "story_prop", "name": name,
                            "position": position, "size": size, "material": material, **extra})

    story("ward_305_clock", "Остановившиеся часы", (5, 2.2, -23.82), (0.72, 0.72, 0.04), "story_clock")
    props.table(11.0, -22.7, 2.0, 0.8, 0.82)
    part((11, 1.35, -22.8), (1.7, 1.15, 0.45), (0.12, 0.14, 0.13))
    story("ward_306_tv", "Старый телевизор", (11, 1.45, -22.53), (1.4, 0.80, 0.035),
          materials={"default": "story_tv_static_a", "noise": "story_tv_static_b", "memory": "story_tv_memory"},
          animated_states=["default", "noise"], emission=[0.035, 0.045, 0.035])
    # The toy sits on the existing 307 bed and remains reachable from its side.
    story("ward_307_toy", "Детская игрушка", (14.83, 0.94, -22.15), (0.32, 0.40, 0.25),
          color=[0.48, 0.31, 0.20])
    for x in (14.72, 14.94):
        part((x, 1.16, -22.15), (0.13, 0.13, 0.13), (0.48, 0.31, 0.20))
        part((x, 1.05, -22.015), (0.04, 0.045, 0.025), (0.06, 0.045, 0.03))
    part((14.83, 0.98, -22.0), (0.13, 0.08, 0.08), (0.65, 0.48, 0.30))
    for x in (14.59, 15.07):
        part((x, 0.88, -22.15), (0.17, 0.24, 0.19), (0.48, 0.31, 0.20))
    for x in (14.72, 14.94):
        part((x, 0.76, -22.03), (0.13, 0.13, 0.22), (0.48, 0.31, 0.20))
    story("ward_308_drawing", "Детский рисунок", (29.82, 1.8, -13.2), (0.85, 0.64, 0.03), "story_drawing", yaw=-90)

    # Child's bed, wardrobe, toys and central key stool leave a route from the door.
    boxes.append(Box((22.9, 0.36, -21), (1.1, 0.22, 2.05), material="wood"))
    part((22.9, 0.54, -21), (1.02, 0.20, 1.95), (0.63, 0.58, 0.45))
    part((22.9, 0.72, -21.67), (0.8, 0.16, 0.42), (0.76, 0.71, 0.60))
    boxes.append(Box((22.9, 0.68, -22.05), (1.13, 1.1, 0.10), material="wood"))
    props.cabinet(28.6, -22.8, 1.8, 1.65, medical=False, yaw=180)
    props.chair(28.0, -18.4, yaw=90)
    props.decorations.append(Box((21.17, 1.65, -19.1), (0.85, 0.64, 0.03), material="story_drawing", local_texture=True, yaw_degrees=90))
    for x, z in ((24.0, -22.8), (21.9, -19.3), (28.2, -21.1)):
        part((x, 0.24, z), (0.35, 0.4, 0.27), (0.41, 0.28, 0.21))
        part((x - 0.12, 0.47, z), (0.13, 0.13, 0.13), (0.41, 0.28, 0.21))
        part((x + 0.12, 0.47, z), (0.13, 0.13, 0.13), (0.41, 0.28, 0.21))
    props.table(24.1, -22.1, 0.65, 0.65, 0.65)
    story("child_music_box", "Музыкальная шкатулка", (24.1, 0.82, -22.1), (0.42, 0.23, 0.32), color=[0.42, 0.29, 0.19])
    part((24.1, 1.0, -22.18), (0.44, 0.05, 0.29), (0.49, 0.34, 0.23))
    definitions.append({"id": "ward_313_key", "type": "key", "name": "Ключ от палаты 313",
                        "key_id": "ward_313", "position": (26, 0, -20), "pedestal": "stool", "initial": "unavailable"})
    for position in CHILD_CAMERAS:
        camera = FixedCameraZone((21, 0, -24), (30, 4.56, -17), position, CHILD_BED_TARGET)
        props.decorations.extend(camera_model_boxes(camera, True, aim_pitch=True))
        part((position[0], min(4.4, position[1] + 0.25), position[2]), (0.08, 0.4, 0.08), (0.18, 0.19, 0.18))
