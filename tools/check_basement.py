"""Спускается обычным контроллером, проверяет большой зал и источники за индексом 128."""

from array import array
import json
import math
from pathlib import Path
from statistics import median
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.core.window import Window
from engine.input.state import InputState
from engine.rendering.renderer import Renderer
from game.effects import create_postprocess_settings
from game.entities.player import create_player
from game.levels import create_level
from game.levels.maze import maze_layout_path
from game.levels.maze_layout import load_maze_layout
from game.materials import create_texture_settings
from tools.check_rendering import save_image


def main():
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    renderer = None
    pygame.init()
    try:
        layout = load_maze_layout(maze_layout_path())
        level = create_level("maze")
        world = CollisionWorld3D((b.collider for b in level.boxes), level.floor_bounds, level.base_height)
        player = create_player(level, world)
        window = Window(settings.WINDOW_SIZE, "Basement lamp hall", settings.OPENGL_VERSION, False, settings.RENDER_SIZE)
        renderer = Renderer(settings.RENDER_SIZE, settings.BACKGROUND_COLOR, settings.OPENGL_VERSION,
                            player.camera, level, textures=create_texture_settings(),
                            postprocess=create_postprocess_settings())
        points = (*reversed(layout.basement.stair_points(layout)), (0, level.base_height, 24))
        simulation_frames = 0
        for target in points:
            for _ in range(2400):
                pygame.event.pump()
                position = player.body.position
                dx, dz = target[0] - position.x, target[2] - position.z
                if math.hypot(dx, dz) < 0.065:
                    assert abs(position.y - target[1]) < 0.02, (position, target)
                    break
                desired = math.degrees(math.atan2(dz, dx))
                turn = (desired - player.controller.yaw_degrees + 180) % 360 - 180
                player.update(1 / 60, InputState(forward=1, sprint=True,
                                               mouse_delta=(round(turn / settings.MOUSE_SENSITIVITY), 0)))
                assert not world.is_blocked(player.body.position, player.body.radius - 1e-5, player.body.height)
                simulation_frames += 1
                if simulation_frames % 15 == 0:
                    renderer.render(window.size)
            else:
                raise AssertionError(f"Player stuck: {player.body.position}, target: {target}")
        assert "FLOOR B1" in player.status_text
        turn = (-90 - player.controller.yaw_degrees + 180) % 360 - 180
        player.update(0, InputState(mouse_delta=(round(turn / settings.MOUSE_SENSITIVITY), -75)))
        renderer.render(window.size)
        target = renderer.output_target
        lit = target.framebuffer.read(components=3, alignment=1)
        # Все подвальные источники имеют индексы > 102; ограничиваем только число ламп для сравнения.
        renderer._program["light_count"].value = len(layout.lighting.lights)
        renderer.render(window.size)
        above_only = target.framebuffer.read(components=3, alignment=1)
        renderer._program["light_count"].value = len(level.lighting.lights)
        brightened = sum(lit[i] > above_only[i] + 5 for i in range(len(lit) // 2))
        assert brightened > 10000, brightened
        values = array("f", renderer._lighting._light_data.read(alignment=1))
        last = len(level.lighting.lights) - 1
        for channel, expected in enumerate((*level.lighting.lights[last].position, level.lighting.lights[last].radius)):
            assert abs(values[last * 4 + channel] - expected) < 0.0001
        timings, gpu = [], []
        query = renderer.context.query(time=True)
        for frame in range(16):
            renderer.context.finish()
            started = perf_counter()
            with query:
                renderer.render(window.size)
            renderer.context.finish()
            if frame >= 4:
                timings.append((perf_counter() - started) * 1000)
                gpu.append(query.elapsed / 1e6)
        renderer.render(window.size, player.status_text,
                        f"BASEMENT: 225 CEILING LAMPS\n" + "\n".join(renderer.debug_lines))
        save_image(output / "basement-hall.png", target.framebuffer.read(components=3, alignment=1), target.size)
        assert renderer.context.error == "GL_NO_ERROR"
        report = {"basement_lamps": len(layout.basement.lights(layout)), "all_lights": len(level.lighting.lights),
                  "room_size": [layout.width, layout.depth], "floor_height": level.base_height,
                  "simulation_frames": simulation_frames, "controller_descent": True,
                  "brightened_channels": brightened, "light_data_over_128": True,
                  "grid_max_candidates": renderer._lighting.grid.max_lights,
                  "color_draws": renderer._draw_calls, "depth_draws": renderer._depth_draw_calls,
                  "frame_median_ms": median(timings), "gpu_query_median_ms": median(gpu),
                  "gl_error": renderer.context.error}
        (output / "basement-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))
    finally:
        if renderer is not None:
            renderer.release()
        pygame.quit()


if __name__ == "__main__":
    main()
