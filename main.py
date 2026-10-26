from config import controls, settings
from engine.collision.world3d import CollisionWorld3D
from engine.core.application import Application
from engine.particles.snow import Snowfall, SnowSettings
from engine.rendering.hud import HudStyle
from game.entities.player import create_player
from game.effects import create_postprocess_settings
from game.materials import create_texture_settings
from game.levels import create_level


def main():
    level = create_level(settings.LEVEL_NAME)
    collision_world = CollisionWorld3D(
        colliders=(box.collider for box in level.boxes),
        bounds=level.floor_bounds,
    )
    player = create_player(level, collision_world)
    snow = None
    if settings.SNOW_ENABLED and level.snow_enabled:
        snow = Snowfall(
            settings=SnowSettings(
                count=settings.SNOW_COUNT,
                height=settings.SNOW_HEIGHT,
                fall_speed=settings.SNOW_FALL_SPEED,
                flake_size=settings.SNOW_FLAKE_SIZE,
                color=settings.SNOW_COLOR,
                seed=settings.SNOW_SEED,
            ),
            bounds=level.floor_bounds,
            obstacles=tuple(box.footprint for box in level.boxes),
        )
    app = Application(
        window_size=settings.WINDOW_SIZE,
        render_size=settings.RENDER_SIZE,
        window_title=settings.WINDOW_TITLE,
        fps_limit=settings.FPS_LIMIT,
        background_color=settings.BACKGROUND_COLOR,
        opengl_version=settings.OPENGL_VERSION,
        vsync=settings.VSYNC,
        controlled_entity=player,
        level=level,
        snow=snow,
        input_bindings=controls.INPUT_BINDINGS,
        textures=create_texture_settings(),
        hud_style=HudStyle(font_size=settings.HUD_FONT_SIZE, margin=settings.HUD_MARGIN),
        postprocess=create_postprocess_settings(),
    )
    app.run()


if __name__ == "__main__":
    main()
