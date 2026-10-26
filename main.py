from config import controls, settings
from engine.collision.world import CollisionWorld
from engine.controllers.first_person import FirstPersonController
from engine.core.application import Application
from engine.scene.camera import Camera
from game.levels import create_level


def main():
    level = create_level(settings.LEVEL_NAME)
    collision_world = CollisionWorld(
        colliders=(box.footprint for box in level.boxes),
        bounds=level.floor_bounds,
    )
    camera = Camera(
        position=level.spawn_position,
        target=level.spawn_target,
        fov_degrees=settings.CAMERA_FOV_DEGREES,
        near=settings.CAMERA_NEAR,
        far=settings.CAMERA_FAR,
    )
    app = Application(
        window_size=settings.WINDOW_SIZE,
        window_title=settings.WINDOW_TITLE,
        fps_limit=settings.FPS_LIMIT,
        background_color=settings.BACKGROUND_COLOR,
        opengl_version=settings.OPENGL_VERSION,
        vsync=settings.VSYNC,
        camera=camera,
        level=level,
        controller=FirstPersonController(
            camera=camera,
            move_speed=settings.MOVE_SPEED,
            mouse_sensitivity=settings.MOUSE_SENSITIVITY,
            pitch_limit_degrees=settings.PITCH_LIMIT_DEGREES,
            max_delta_time=settings.MAX_DELTA_TIME,
            player_radius=settings.PLAYER_RADIUS,
            collision_max_step=settings.COLLISION_MAX_STEP,
            collision_world=collision_world,
        ),
        input_bindings=controls.INPUT_BINDINGS,
    )
    app.run()


if __name__ == "__main__":
    main()
