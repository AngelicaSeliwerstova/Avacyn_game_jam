"""Проверка снега в настоящем OpenGL-окне без захвата мыши."""

from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
import glm

from config import settings
from engine.collision.aabb import AABB
from engine.core.window import Window
from engine.particles.snow import Snowfall, SnowSettings
from engine.rendering.renderer import Renderer
from engine.rendering.snow import SnowRenderer
from engine.scene.box import Box
from engine.scene.camera import Camera
from engine.scene.level import Level
from game.levels import create_level
from game.materials import create_texture_settings
from tools.check_rendering import expected_window, read_window, save_image


def main():
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    renderer = None
    pygame.init()
    try:
        window = Window(settings.WINDOW_SIZE, "Snow check", settings.OPENGL_VERSION,
                        settings.VSYNC, settings.RENDER_SIZE)
        level = create_level("corridor")
        snow_settings = SnowSettings(
            settings.SNOW_COUNT, settings.SNOW_HEIGHT, settings.SNOW_FALL_SPEED,
            settings.SNOW_FLAKE_SIZE, settings.SNOW_COLOR, settings.SNOW_SEED,
        )
        snow = Snowfall(snow_settings, level.floor_bounds, tuple(box.footprint for box in level.boxes))
        camera = Camera(level.spawn_position, level.spawn_target, settings.CAMERA_FOV_DEGREES,
                        settings.CAMERA_NEAR, settings.CAMERA_FAR)
        renderer = Renderer(settings.RENDER_SIZE, settings.BACKGROUND_COLOR,
                            settings.OPENGL_VERSION, camera, level, snow,
                            textures=create_texture_settings())

        def capture():
            renderer.render(window.size)
            assert renderer.context.error == "GL_NO_ERROR"
            return renderer._render_target.framebuffer.read(components=3, alignment=1)

        initial = capture()
        assert initial == capture(), "Rendering alone must not move snow"
        assert read_window(renderer, window.size) == expected_window(
            initial, settings.RENDER_SIZE, window.size,
        ), "Snow must use the same integer scaling as the scene"
        save_image(output / "snow-start.png", initial, settings.RENDER_SIZE)
        for _ in range(120):
            pygame.event.pump()
            snow.update(1 / 60)
            capture()
            window.present()
        fallen = capture()
        assert initial != fallen, "Snow must move over time"
        save_image(output / "snow-fallen.png", fallen, settings.RENDER_SIZE)

        # Все частицы за стеной: кадр должен совпасть с вариантом без снега.
        wall = Box(position=(0, 2, -2), size=(10, 4, 1))
        wall_level = Level((20, 20), 1, (wall,), (0, 1.6, 4), (0, 1.6, 0), settings.FLOOR_COLORS)
        camera.position = glm.vec3(wall_level.spawn_position)
        camera.target = glm.vec3(wall_level.spawn_target)
        hidden_snow = Snowfall(replace(snow_settings, count=100, height=3),
                               AABB(-1, -8, 1, -6), ())
        renderer._level = wall_level
        baseline_snow = renderer._snow
        renderer._snow = None
        without_snow = capture()
        renderer._snow = baseline_snow
        # Отдельный GPU-эффект, тот же контекст и глубина.
        hidden_renderer = SnowRenderer(renderer.context, hidden_snow, camera, settings.RENDER_SIZE)
        try:
            renderer._snow = hidden_renderer
            assert capture() == without_snow, "Wall must hide snow behind it"
            renderer._level = replace(wall_level, boxes=())
            visible = capture()
            renderer._snow = None
            assert visible != capture(), "The same particles must be visible without the wall"
        finally:
            renderer._snow = baseline_snow
            hidden_renderer.release()

        report = {"frames": 120, "particles": snow_settings.count, "motion": True,
                  "stable_without_update": True, "integer_scaling": True,
                  "wall_occlusion": True, "gl_error": renderer.context.error}
        (output / "snow-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))
    finally:
        if renderer is not None:
            renderer.release()
        pygame.quit()


if __name__ == "__main__":
    main()
