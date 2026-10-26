from config import settings
from engine.core.application import Application


def main():
    app = Application(
        window_size=settings.WINDOW_SIZE,
        window_title=settings.WINDOW_TITLE,
        fps_limit=settings.FPS_LIMIT,
        background_color=settings.BACKGROUND_COLOR,
        opengl_version=settings.OPENGL_VERSION,
        vsync=settings.VSYNC,
    )
    app.run()


if __name__ == "__main__":
    main()
