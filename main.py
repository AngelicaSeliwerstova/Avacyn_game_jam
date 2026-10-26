from config import controls, settings
from engine.collision.world3d import CollisionWorld3D
from engine.controllers.first_person import FirstPersonController
from engine.core.application import Application
from engine.particles.snow import Snowfall, SnowSettings
from engine.physics.character import CharacterBody
from engine.scene.camera import Camera
from game.levels import create_level


def main():
    level = create_level(settings.LEVEL_NAME)
    collision_world = CollisionWorld3D(
        colliders=(box.collider for box in level.boxes),
        bounds=level.floor_bounds,
    )
    x, y, z = level.spawn_position
    body = CharacterBody(
        position=(x, y - settings.PLAYER_EYE_HEIGHT, z),
        world=collision_world,
        radius=settings.PLAYER_RADIUS,
        height=settings.PLAYER_HEIGHT,
        step_height=settings.PLAYER_STEP_HEIGHT,
        gravity=settings.GRAVITY,
        collision_max_step=settings.COLLISION_MAX_STEP,
        physics_step=settings.PHYSICS_STEP,
        camera_smoothing=settings.STAIR_CAMERA_SMOOTHING,
    )
    camera = Camera(
        position=level.spawn_position,
        target=level.spawn_target,
        fov_degrees=settings.CAMERA_FOV_DEGREES,
        near=settings.CAMERA_NEAR,
        far=settings.CAMERA_FAR,
    )
    snow = None
    if settings.SNOW_ENABLED:
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
        camera=camera,
        level=level,
        snow=snow,
        controller=FirstPersonController(
            camera=camera,
            move_speed=settings.MOVE_SPEED,
            mouse_sensitivity=settings.MOUSE_SENSITIVITY,
            pitch_limit_degrees=settings.PITCH_LIMIT_DEGREES,
            max_delta_time=settings.MAX_DELTA_TIME,
            player_radius=settings.PLAYER_RADIUS,
            collision_max_step=settings.COLLISION_MAX_STEP,
            body=body,
            eye_height=settings.PLAYER_EYE_HEIGHT,
        ),
        input_bindings=controls.INPUT_BINDINGS,
    )
    app.run()


if __name__ == "__main__":
    main()
