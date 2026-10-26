from config import settings
from engine.scene.box import Box
from engine.scene.level import Level


def create_demo_level() -> Level:
    return Level(
        floor_size=settings.FLOOR_SIZE,
        floor_tile_size=settings.FLOOR_TILE_SIZE,
        boxes=(Box(position=settings.CUBE_POSITION, size=settings.CUBE_SIZE,
                   material=settings.DEMO_CUBE_MATERIAL),),
        spawn_position=settings.CAMERA_POSITION,
        spawn_target=settings.CAMERA_TARGET,
        floor_colors=settings.FLOOR_COLORS,
        floor_material=settings.DEMO_FLOOR_MATERIAL,
    )
