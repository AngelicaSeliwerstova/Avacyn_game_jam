"""Проходит лабиринт обычным контроллером и сохраняет план и GPU-кадры."""

import json
import math
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import glm
import pygame

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.core.window import Window
from engine.input.state import InputState
from engine.rendering.renderer import Renderer
from game.entities.player import create_player
from game.effects import create_postprocess_settings
from game.levels import create_level
from game.levels.maze import maze_layout_path
from game.levels.maze_layout import load_maze_layout
from game.materials import create_texture_settings
from tools.check_rendering import save_image


def save_plan(layout, level, path):
    scale, margin, gap, header = 6, 20, 24, 32
    panel_width = round(level.floor_size[0] * scale)
    height = round(level.floor_size[1] * scale)
    image = pygame.Surface((2 * panel_width + gap + 2 * margin, height + header + 2 * margin))
    image.fill((20, 21, 25))
    font = pygame.font.Font(None, 20)

    for floor, rows in enumerate(layout.floors):
        ox = margin + floor * (panel_width + gap)

        def pixel(x, z):
            return round(ox + (x + level.floor_size[0] / 2) * scale), round(
                margin + header + (z + level.floor_size[1] / 2) * scale,
            )

        image.blit(font.render(f"FLOOR {floor + 1}", False, (230, 230, 220)), (ox, margin))
        for row, cells in enumerate(rows):
            for column, cell in enumerate(cells):
                x, _, z = layout.position((floor, row, column))
                left, top = pixel(x - layout.cell_size / 2, z - layout.cell_size / 2)
                side = round(layout.cell_size * scale)
                color = (58, 61, 66) if cell == "#" else (189, 184, 164)
                pygame.draw.rect(image, color, (left, top, side, side))
        for link in layout.stairs:
            lower, bottom, top, upper = layout.stair_points(link)
            wing_min = min(bottom[2], top[2]) - layout.cell_size / 2
            wing_max = max(bottom[2], top[2]) + layout.cell_size / 2
            left, top_y = pixel(bottom[0] - layout.wing_width / 2, wing_min)
            pygame.draw.rect(image, (115, 93, 61), (left, top_y, round(layout.wing_width * scale),
                                                   round((wing_max - wing_min) * scale)))
            pygame.draw.line(image, (240, 177, 68), pixel(bottom[0], bottom[2]),
                             pixel(top[0], top[2]), 4)
            door = lower if floor == 0 else upper
            pygame.draw.line(image, (240, 177, 68), pixel(bottom[0], door[2]), pixel(door[0], door[2]), 4)
            image.blit(font.render(link.name, False, (255, 238, 185)), (left + 5, top_y + 4))
        if floor == 0:
            if layout.basement is not None:
                bx, _, bz = layout.position(layout.basement.entry)
                pygame.draw.circle(image, (160, 125, 255), pixel(bx, bz), 5)
                image.blit(font.render("B1 DOWN", False, (190, 165, 255)), pixel(bx - 8, bz + 2))
            x, _, z = layout.position(layout.spawn)
            pygame.draw.circle(image, (70, 160, 255), pixel(x, z), 5)
            image.blit(font.render("START", False, (70, 160, 255)), pixel(x + 1, z))
        else:
            x, _, z = layout.goal_position
            left, top = pixel(x - layout.cell_size / 2, -layout.depth / 2 - layout.balcony_depth)
            pygame.draw.rect(image, (48, 118, 76), (left, top, round(layout.cell_size * scale),
                                                  round(layout.balcony_depth * scale)))
            image.blit(font.render("EXIT", False, (110, 240, 145)), pixel(x + 2, z))
    pygame.image.save(image, str(path))


def main():
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    renderer = None
    pygame.init()
    try:
        layout = load_maze_layout(maze_layout_path())
        level = create_level("maze")
        world = CollisionWorld3D((box.collider for box in level.boxes), level.floor_bounds, level.base_height)
        player = create_player(level, world)
        points = layout.walk_points(layout.path(layout.spawn, layout.exit)) + (layout.goal_position,)
        save_plan(layout, level, output / "maze-plan.png")
        window = Window(settings.WINDOW_SIZE, "Maze check", settings.OPENGL_VERSION,
                        settings.VSYNC, settings.RENDER_SIZE)
        renderer = Renderer(settings.RENDER_SIZE, settings.BACKGROUND_COLOR, settings.OPENGL_VERSION,
                            player.camera, level, textures=create_texture_settings(),
                            postprocess=create_postprocess_settings())
        snapshots = set()
        timings = []

        def draw(name=None):
            start = perf_counter()
            renderer.render(window.size, hud_text=player.status_text)
            window.present()
            timings.append((perf_counter() - start) * 1000)
            assert renderer.context.error == "GL_NO_ERROR"
            if name is not None:
                target = renderer.output_target
                save_image(output / f"maze-{name}.png", target.framebuffer.read(components=3, alignment=1), target.size)
                snapshots.add(name)

        draw("start")
        index = 1
        for frame in range(20000):
            pygame.event.pump()
            target = points[index]
            position = player.body.position
            dx, dz = target[0] - position.x, target[2] - position.z
            if math.hypot(dx, dz) < 0.065:
                assert abs(position.y - target[1]) < 0.02, (index, target, position)
                index += 1
                if index == len(points):
                    break
                continue
            desired = math.degrees(math.atan2(dz, dx))
            turn = (desired - player.controller.yaw_degrees + 180) % 360 - 180
            player.update(1 / 60, InputState(forward=1, sprint=True,
                                           mouse_delta=(round(turn / settings.MOUSE_SENSITIVITY), 0)))
            assert not world.is_blocked(player.body.position, player.body.radius - 1e-5, player.body.height)
            if "STAIRS" in player.status_text and "stairs" not in snapshots:
                draw("stairs")
            elif (player.body.position.y >= layout.floor_height - 0.02
                  and abs(player.body.position.x) < layout.width / 2 - 2 and "upper" not in snapshots):
                draw("upper")
            elif frame % 6 == 0:
                draw()
        else:
            raise AssertionError(f"Player stuck before waypoint {index}: {player.body.position}")
        assert "EXIT FOUND" in player.status_text
        player.update(0, InputState(mouse_delta=(round(180 / settings.MOUSE_SENSITIVITY), 100)))
        draw("exit")
        assert {"start", "stairs", "upper", "exit"} <= snapshots
        report = {"size": level.floor_size, "boxes": len(level.boxes), "floors": level.floor_heights,
                  "simulation_frames": frame, "gpu_frames": len(timings), "exit_found": True,
                  "average_render_ms": sum(timings) / len(timings), "gl_error": renderer.context.error}
        (output / "maze-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))
    finally:
        if renderer is not None:
            renderer.release()
        pygame.quit()


if __name__ == "__main__":
    main()
