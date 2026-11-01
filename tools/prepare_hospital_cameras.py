"""Author the hospital's fixed shots. Run with --write to replace camera JSONs.

Coordinates are in metres, relative to each storey. Opposing room shots cover
both the doorway and the far wall; corridor cuts preserve the direction of travel.
The generated JSONs remain independently editable in Creator (F6).
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.scene.camera import FixedCameraZone
from game.levels.cameras import save_fixed_cameras
from game.levels.spiral import SpiralStair


def hospital_cameras():
    shots = []

    def shot(floor, bounds, position, target):
        y = floor * 4.8
        x1, z1, x2, z2 = bounds
        shots.append(FixedCameraZone(
            (x1, y + 0.45, z1), (x2, y + 2.85, z2),
            (position[0], position[1] + y, position[2]),
            (target[0], target[1] + y, target[2]),
        ))

    def room(floor, bounds, height=3.35):
        x1, z1, x2, z2 = bounds
        cx, cz = (x1 + x2) / 2, (z1 + z2) / 2
        # Look into the room from opposite corners, never through its walls.
        shot(floor, (x1, z1, x2, cz), (x2 - .6, height, z2 - .6), (cx, .95, z1 + (z2-z1)*.28))
        shot(floor, (x1, cz, x2, z2), (x1 + .6, height, z1 + .6), (cx, 1.0, z1 + (z2-z1)*.72))

    def corridor(floor, bounds, height=3.5):
        x1, z1, x2, z2 = bounds
        cx, cz = (x1 + x2) / 2, (z1 + z2) / 2
        shot(floor, (x1, z1, cx, z2), (x2 - .5, height, z1 + .5), (x1 + (x2-x1)*.3, 1, cz))
        shot(floor, (cx, z1, x2, z2), (x1 + .5, height, z2 - .5), (x1 + (x2-x1)*.7, 1, cz))

    # Ground floor: the doctor's desk, treatment rooms and twin-bed wards.
    for left, right in zip((-21, -14, -7, 0, 7, 14), (-14, -7, 0, 7, 14, 21)):
        room(0, (left + .15, -13.85, right - .15, -5.85), 3.05)
    # Long north corridor, with oblique views along the row of office doors.
    for left, right in ((-20.85, -12), (-12, -5.85)):
        corridor(0, (left, -5.95, right, -2.1), 3.1)
    for left, right in ((-5.85, 3), (3, 12), (12, 20.85)):
        corridor(0, (left, -5.95, right, .1), 3.2)
    # The north vestibule can look back at the door; the terminal approach
    # must see the front of its screen, even when arriving from the hall.
    shot(0, (-5.85, -.1, -.15, 1.2), (-.75, 3.15, 7.5), (-3, 1, 1.8))
    shot(0, (-5.85, 5.8, -.15, 8.1), (-5.25, 3.15, .5), (-3, 1, 6.7))
    # Reception: counter, east staff entrance, and the plan behind the desk.
    for bounds in ((5.1, 3.8, 18.1, 6.6), (5.1, .1, 11.3, 3.8), (15.5, .1, 18.1, 3.8)):
        shot(0, bounds, (17.3, 3.65, 5.9), (10.7, 1.25, 1.7))
    shot(0, (11.3, .15, 15.5, 3.8), (13.4, 3.7, 8), (13.4, 2.1, .17))
    shot(0, (-5.85, 1.2, -.15, 5.8), (-5.2, 3.1, .7), (-2.75, 1.22, 4.9))
    shot(0, (18.1, -.1, 20.85, 7.3), (20.4, 3.3, -.6), (17.5, 1, 5.4))
    shot(0, (0, -.1, 5.1, 8), (1, 3.5, -.5), (3, 1, 7))
    # Entrance hall: wide establishing shots, benches, and the stair approach.
    shot(0, (-6, 8, 7, 13.85), (-5.4, 3.7, 13.3), (4, .9, 8.9))
    shot(0, (7, 6.6, 20.85, 13.85), (20.35, 3.65, 13.25), (11, 1, 7.8))
    shot(0, (-20.85, 8.7, -6, 13.85), (-20.3, 3.55, 13.2), (-10, 1, 9.7))
    shot(0, (-20.85, -1.85, -17.2, 8.7), (-20.35, 3.7, -1.35), (-18.5, 1, 6))
    shot(0, (-17.2, -1.85, -6.15, .1), (-6.7, 3.5, -1.3), (-15.5, 1, -.5))
    shot(0, (-8.7, .1, -6.15, 8.7), (-6.7, 3.6, -.9), (-7.4, 1, 7))
    shot(0, (-5.9, -2, 0, .1), (-.6, 3.35, -2.8), (-4.8, 1, -1))
    shot(0, (-15, .5, -11, 5.5), (-13, 5.5, 4), (-13, .8, 3.5))

    # Surgery: seven deep north rooms, the open hall, and southern service rooms.
    for left, right in zip((-30, -20, -12, -4, 4, 12, 20), (-20, -12, -4, 4, 12, 20, 30)):
        room(1, (left + .15, -23.85, right - .15, -9.85))
    for left, right in ((-29.85, -20), (-20, -10), (-10, 0), (0, 10), (10, 20), (20, 29.85)):
        corridor(1, (left, -9.9, right, -2.1), 3.6)
    for bounds in ((-4.85, -1.85, 3.85, 7.85), (4.15, -1.85, 15.85, 7.85),
                   (16.15, -1.85, 29.85, 7.85), (-4.85, 14.1, 13.85, 23.85),
                   (14.15, 14.1, 29.85, 23.85)):
        room(1, bounds, 3.7)
    for left, right in ((-4.85, 7), (7, 18), (18, 29.85)):
        corridor(1, (left, 7.9, right, 14.1), 3.65)
    for z1, z2 in ((-2.1, 10), (10, 23.85)):
        room(1, (-29.85, z1, -17.7, z2), 3.7)
    shot(1, (-17.7, 8.65, -4.85, 16), (-5.5, 3.7, 13.4), (-14.5, 1, 10.2))
    shot(1, (-17.7, 16, -4.85, 23.85), (-5.5, 3.7, 23.2), (-14.5, 1, 17.5))
    shot(1, (-8.65, -2.1, -5, 8.65), (-5.6, 3.6, -1.5), (-7.3, 1, 6.8))
    shot(1, (-17.7, -2.1, -8.65, -.65), (-17.1, 3.3, -1.25), (-10, 1, -1.2))

    # Patient floor: the final north room is divided into an anteroom and nursery.
    for left, right in zip((-30, -21, -14, -7, 0, 7, 14), (-21, -14, -7, 0, 7, 14, 21)):
        room(2, (left + .15, -23.85, right - .15, -9.85))
    room(2, (21.15, -16.85, 29.85, -9.85), 3.1)
    room(2, (21.15, -23.85, 29.85, -16.85), 3.25)
    for left, right in ((-29.85, -20), (-20, -10.15), (-3.85, 7), (7, 18), (18, 29.85)):
        corridor(2, (left, -9.9, right, -4.1), 3.5)
    room(2, (-9.85, -9.85, -4.15, -3.85), 3.1)
    for bounds in ((16.1, -3.85, 29.85, 1.85), (16.1, 2.15, 29.85, 7.85),
                   (2.15, 14.1, 15.85, 23.85), (16.15, 14.1, 29.85, 23.85)):
        room(2, bounds, 3.6)
    # Wide southwest ward needs two overlapping compositions across its length.
    room(2, (-29.85, 14.1, -14, 23.85), 3.7)
    room(2, (-14, 14.1, 1.85, 23.85), 3.7)
    for left, right in ((-5, 5), (5, 12)):
        room(2, (left, -4, right, 8.2), 3.7)
    room(2, (12, -4, 15.9, 2.5), 3.7)
    shot(2, (12, 7.7, 15.9, 8.2), (6, 3.7, 10), (14, 1, 7.9))
    for left, right in ((-17.7, -5), (-5, 7), (7, 18), (18, 29.85)):
        corridor(2, (left, 8.2, right, 14.1), 3.7)
    for z1, z2 in ((-4.1, 5), (5, 14)):
        room(2, (-29.85, z1, -17.7, z2), 3.65)
    shot(2, (-17.7, -4.1, -10.15, -.65), (-17.1, 3.5, -3.5), (-11, 1, -1.3))
    shot(2, (-10.15, -4.1, -5, -.65), (-5.6, 3.5, -3.5), (-9, 1, -1.3))
    shot(2, (-8.65, -.65, -5, 8.2), (-5.6, 3.6, -1.5), (-7.3, 1, 6.8))
    shot(2, (12, 2.5, 15.9, 7.7), (10, 3.5, 1.7), (16, 1.5, 5))
    for floor in (1, 2):
        shot(floor, (-13.5, 5.5, -7, 8.5), (-6.5, 3.65, 11.2), (-11.5, 1, 6.6))

    # Spiral: short overlapping sectors follow the rise without looking through
    # the inner parapet or the slabs. Each lens stays over its own flight.
    stair = SpiralStair()
    path = stair.walking_path()
    for index in range(0, len(path), 4):
        segment = path[index:index + 4]
        middle = min(index + 2, len(path) - 1)
        angle = 90 - (middle + .5) * 10
        x, y, z = path[middle]
        position = stair.point(angle + 65, 3.9, y + 2.8)
        target = stair.point(angle, 2.9, y + 1.05)
        shots.append(FixedCameraZone(
            (min(p[0] for p in segment) - .9, min(p[1] for p in segment) + .5, min(p[2] for p in segment) - .9),
            (max(p[0] for p in segment) + .9, max(p[1] for p in segment) + 2.5, max(p[2] for p in segment) + .9),
            position, target,
        ))
    return tuple(shots)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="replace the four authored camera files")
    args = parser.parse_args()
    cameras = hospital_cameras()
    print(f"{len(cameras)} fixed shots per hospital layout")
    if args.write:
        root = Path(__file__).resolve().parents[1] / "resources/levels"
        for name in ("peaceful", "start", "act1", "act2"):
            save_fixed_cameras(root / f"{name}_cameras.json", cameras)
