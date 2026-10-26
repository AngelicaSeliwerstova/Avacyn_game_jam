"""Сравнивает кадры и время CPU/GPU с оптимизациями и без на одной карте."""

from dataclasses import replace
import json
import math
from pathlib import Path
from statistics import median
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import glm
import pygame

from config import settings
from engine.core.window import Window
from engine.rendering.options import RenderOptions
from engine.rendering.renderer import Renderer
from engine.scene.camera import Camera
from game.effects import create_postprocess_settings
from game.levels import create_level
from game.levels.maze import maze_layout_path
from game.levels.maze_layout import load_maze_layout
from game.materials import create_texture_settings
from tools.check_rendering import save_image


def views(level, layout):
    pose = glm.vec3(-27.44, 5.20, 12.13)
    yaw, pitch = math.radians(308.4), math.radians(-12.1)
    direction = glm.vec3(math.cos(yaw) * math.cos(pitch), math.sin(pitch), math.sin(yaw) * math.cos(pitch))
    _, bottom, top, _ = layout.stair_points(layout.stairs[0])
    eye = glm.vec3(0, settings.PLAYER_EYE_HEIGHT, 0)
    return (
        ("spawn", level.spawn_position, level.spawn_target),
        ("reported_wall", tuple(pose), tuple(pose + direction)),
        ("stairs", tuple(glm.vec3(bottom) + eye), tuple(glm.vec3(top) + eye)),
        ("upper", tuple(glm.vec3(layout.position((1, 1, 9))) + eye),
         tuple(glm.vec3(layout.position((1, 1, 14))) + eye)),
        ("exit", tuple(glm.vec3(layout.goal_position) + eye),
         tuple(glm.vec3(layout.position(layout.exit)) + eye)),
    )


def measure(renderer, window, query):
    wall, cpu, gpu = [], [], []
    for frame in range(8):
        pygame.event.pump()
        renderer.context.finish()
        start = perf_counter()
        with query:
            renderer.render(window.size)
        submitted = perf_counter()
        renderer.context.finish()
        finished = perf_counter()
        if frame >= 2:
            wall.append((finished - start) * 1000)
            cpu.append((submitted - start) * 1000)
            gpu.append(query.elapsed / 1e6)
    return {"frame_median_ms": median(wall), "submit_median_ms": median(cpu),
            "gpu_query_median_ms": median(gpu), "frame_p95_ms": sorted(wall)[-1],
            "color_draws": renderer._draw_calls, "depth_draws": renderer._depth_draw_calls,
            "color_triangles": renderer._submitted_triangles}


def main():
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    renderer = None
    pygame.init()
    try:
        layout = load_maze_layout(maze_layout_path())
        level = create_level("maze")
        camera = Camera(level.spawn_position, level.spawn_target, settings.CAMERA_FOV_DEGREES,
                        settings.CAMERA_NEAR, settings.CAMERA_FAR)
        # VSync выключен, время завершения GPU учитывается явно, без ограничения FPS.
        window = Window(settings.WINDOW_SIZE, "Rendering performance", settings.OPENGL_VERSION,
                        False, settings.RENDER_SIZE)
        renderer = Renderer(settings.RENDER_SIZE, settings.BACKGROUND_COLOR, settings.OPENGL_VERSION,
                            camera, level, textures=create_texture_settings(),
                            postprocess=create_postprocess_settings())
        query = renderer.context.query(time=True)
        baseline = RenderOptions(False, False, False)
        modes = {"baseline": baseline, "culling": replace(baseline, frustum_culling=True),
                 "local_lights": replace(baseline, local_lights=True), "optimized": RenderOptions()}
        checks = []
        for name, position, target in views(level, layout):
            camera.position, camera.target = glm.vec3(position), glm.vec3(target)
            renderer.options = baseline
            renderer.render(window.size)
            reference = renderer.output_target.framebuffer.read(components=3, alignment=1)
            timings = {}
            for mode, options in modes.items():
                renderer.options = options
                renderer.render(window.size)
                actual = renderer.output_target.framebuffer.read(components=3, alignment=1)
                differences = [abs(a - b) for a, b in zip(reference, actual)]
                maximum = max(differences)
                changed = sum(d != 0 for d in differences)
                if maximum:
                    save_image(output / f"performance-{name}-reference.png", reference, settings.RENDER_SIZE)
                    save_image(output / f"performance-{name}-{mode}.png", actual, settings.RENDER_SIZE)
                # Смена порядка глубины может изменить единичные пиксели на стыках граней.
                # Отсечение и списки ламп отдельно должны сохранять кадр с точностью 1/255.
                edge_pixels = sum(any(d > 1 for d in differences[i:i + 3])
                                  for i in range(0, len(differences), 3))
                assert maximum <= 1 or (options.depth_prepass and edge_pixels <= 8), (
                    name, mode, maximum, changed, edge_pixels)
                measured = measure(renderer, window, query) if name == "reported_wall" else {
                    "color_draws": renderer._draw_calls, "depth_draws": renderer._depth_draw_calls,
                    "color_triangles": renderer._submitted_triangles,
                }
                timings[mode] = {**measured, "max_channel_error": maximum,
                                 "changed_channels": changed, "edge_pixels": edge_pixels}
            if name == "reported_wall":
                renderer.options = RenderOptions()
                renderer.render(window.size)
                save_image(output / "performance-wall.png", renderer.output_target.framebuffer.read(
                    components=3, alignment=1), settings.RENDER_SIZE)
            checks.append({"view": name, "modes": timings})
            print(json.dumps(checks[-1]), flush=True)
        assert renderer.context.error == "GL_NO_ERROR"
        grid = renderer._lighting.grid
        report = {"gpu": renderer.context.info["GL_RENDERER"], "render_size": settings.RENDER_SIZE,
                  "timed_view": "reported_wall", "samples_per_mode": 6,
                  "light_grid_max_candidates": grid.max_lights if grid else None,
                  "checks": checks, "gl_error": renderer.context.error}
        (output / "performance-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    finally:
        if renderer is not None:
            renderer.release()
        pygame.quit()


if __name__ == "__main__":
    main()
