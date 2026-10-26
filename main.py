from config import controls, settings
from engine.controllers.first_person import FirstPersonController
from engine.core.application import Application
from engine.scene.camera import Camera


def main():
    camera = Camera(
        position=settings.CAMERA_POSITION,
        target=settings.CAMERA_TARGET,
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
        controller=FirstPersonController(
            camera=camera,
            move_speed=settings.MOVE_SPEED,
            mouse_sensitivity=settings.MOUSE_SENSITIVITY,
            pitch_limit_degrees=settings.PITCH_LIMIT_DEGREES,
            max_delta_time=settings.MAX_DELTA_TIME,
        ),
        input_bindings=controls.INPUT_BINDINGS,
    )
    app.run()


if __name__ == "__main__":
    main()
