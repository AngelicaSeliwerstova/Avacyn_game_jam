from config import settings
from engine.scene.box import Box
from engine.scene.level import Level


def create_stairs_level() -> Level:
    boxes = []
    for index in range(settings.STAIRS_COUNT):
        height = (index + 1) * settings.STAIRS_RISE
        z = settings.STAIRS_START_Z - (index + 0.5) * settings.STAIRS_RUN
        boxes.append(Box((0, height / 2, z), (settings.STAIRS_WIDTH, height, settings.STAIRS_RUN),
                         material=settings.STAIRS_STEP_MATERIAL))
    height = settings.STAIRS_COUNT * settings.STAIRS_RISE
    landing_z = (settings.STAIRS_START_Z - settings.STAIRS_COUNT * settings.STAIRS_RUN
                 - settings.STAIRS_LANDING_DEPTH / 2)
    boxes.append(Box((0, height / 2, landing_z),
                     (settings.STAIRS_LANDING_WIDTH, height, settings.STAIRS_LANDING_DEPTH),
                     material=settings.STAIRS_LANDING_MATERIAL))
    x, y, z = settings.STAIRS_SPAWN
    return Level(
        floor_size=settings.FLOOR_SIZE,
        floor_tile_size=settings.FLOOR_TILE_SIZE,
        boxes=tuple(boxes),
        spawn_position=(x, y, z),
        spawn_target=(x, y, z - 1),
        floor_colors=settings.FLOOR_COLORS,
        floor_material=settings.STAIRS_FLOOR_MATERIAL,
    )
