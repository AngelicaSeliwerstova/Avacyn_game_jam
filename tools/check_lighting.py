"""GPU-проверка затухания света, шести граней теней и перекрытий."""

from array import array
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import glm
import pygame

from config import settings
from engine.core.window import Window
from engine.rendering.renderer import Renderer
from engine.scene.box import Box
from engine.scene.camera import Camera
from engine.scene.level import Level
from engine.scene.lighting import Lighting, PointLight
from game.effects import create_postprocess_settings
from game.levels import create_level
from game.materials import create_texture_settings
from tools.check_rendering import save_image


def check_shadows(window):
    size = (320, 240)
    light = PointLight((-2, 3, 0), (0.6, 0.8, 1.0), 3, 10)
    # Свет над перекрытием не должен освещать пол нижнего этажа.
    upstairs = PointLight((-2, 6, 0), (1, 0.4, 0.1), 5, 10)
    probe_light = PointLight((20, 4, 0), radius=6)
    boxes = [Box((0, 3, 0), (0.4, 6, 8)), Box((-2, 4, 0), (10, 0.3, 10))]
    # Шесть препятствий на одинаковом расстоянии проверяют ориентацию всех граней атласа.
    for axis in range(3):
        for sign in (-1, 1):
            position = list(probe_light.position)
            position[axis] += sign * 2
            boxes.append(Box(tuple(position), (0.4, 0.4, 0.4)))
    level = Level((14, 14), 1, tuple(boxes), (0, 12, 0.01), (0, 0, 0),
                  ((180, 180, 180),) * 2,
                  lighting=Lighting((0.08, 0.08, 0.08), (light, upstairs, probe_light)))
    # Камера под перекрытием смотрит на два участка пола с разных сторон стены.
    camera = Camera((0, 3.6, 6), (0, 0, 0), 85, 0.1, 100)
    renderer = Renderer(size, (0, 0, 0), settings.OPENGL_VERSION, camera, level)
    white = None
    try:
        def draw():
            renderer.render(window.size)
            return renderer.output_target.framebuffer.read(components=3, alignment=1)

        def sample(data, point):
            clip = camera.projection_matrix(size[0] / size[1]) * camera.view_matrix * glm.vec4(*point, 1)
            px = int((clip.x / clip.w * 0.5 + 0.5) * size[0])
            py = int((clip.y / clip.w * 0.5 + 0.5) * size[1])
            assert 1 <= px < size[0] - 1 and 1 <= py < size[1] - 1, (px, py)
            pixels = [data[(y * size[0] + x) * 3:(y * size[0] + x) * 3 + 3]
                      for x in range(px - 1, px + 2) for y in range(py - 1, py + 2)]
            return tuple(round(sum(p[c] for p in pixels) / len(pixels)) for c in range(3))

        shadowed = draw()
        assert draw() == shadowed, "Static lighting must not flicker"
        lit = sample(shadowed, (-2, 0, 0))
        dark = sample(shadowed, (2, 0, 0))
        far = sample(shadowed, (-6, 0, 0))
        assert lit[2] > lit[0] + 15, lit
        assert max(dark) <= 18, dark
        assert lit[2] > far[2] + 20, (lit, far)
        renderer._program["light_count"].value = 1
        assert draw() == shadowed, "Upper-floor light must be stopped by the slab"
        renderer._program["light_count"].value = 3

        atlas = renderer._lighting._texture
        depths = array("f", atlas.read(alignment=1))
        resolution = level.lighting.shadow_resolution
        expected = 6 / (6 - 0.05) - 6 * 0.05 / ((6 - 0.05) * 1.8)
        for face in range(6):
            x = (2 * 3 + face % 3) * resolution + resolution // 2
            y = (face // 3) * resolution + resolution // 2
            assert abs(depths[y * atlas.width + x] - expected) < 0.0001, (face, depths[y * atlas.width + x])

        white = renderer.context.texture((1, 1), 1, array("f", [1.0]).tobytes(), dtype="f4")
        renderer._lighting._texture = white
        try:
            no_shadows = draw()
        finally:
            renderer._lighting._texture = atlas
        unblocked = sample(no_shadows, (2, 0, 0))
        assert unblocked[2] > dark[2] + 25, (unblocked, dark)
        assert renderer.context.error == "GL_NO_ERROR"
        return {"lit_rgb": lit, "shadow_rgb": dark, "far_rgb": far,
                "without_shadows_rgb": unblocked, "all_six_shadow_faces": True,
                "ceiling_blocks_light": True, "stable_frames": True}
    finally:
        if white is not None:
            white.release()
        renderer.release()


def main():
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    pygame.init()
    renderer = None
    try:
        window = Window(settings.WINDOW_SIZE, "Lighting check", settings.OPENGL_VERSION,
                        settings.VSYNC, settings.RENDER_SIZE)
        report = check_shadows(window)
        level = create_level("maze")
        camera = Camera(level.spawn_position, level.spawn_target, settings.CAMERA_FOV_DEGREES,
                        settings.CAMERA_NEAR, settings.CAMERA_FAR)
        renderer = Renderer(settings.RENDER_SIZE, settings.BACKGROUND_COLOR, settings.OPENGL_VERSION,
                            camera, level, textures=create_texture_settings(),
                            postprocess=create_postprocess_settings())
        renderer.render(window.size)
        target = renderer.output_target
        after = target.framebuffer.read(components=3, alignment=1)
        save_image(output / "lighting-after.png", after, target.size)
        renderer._program["lighting_enabled"].value = False
        renderer.render(window.size)
        save_image(output / "lighting-before.png", target.framebuffer.read(components=3, alignment=1), target.size)
        renderer._program["lighting_enabled"].value = True
        for frame in range(60):
            camera.position.x += 0.003
            camera.target.x += 0.003
            renderer.render(window.size, "FLOOR 1 / 2")
        assert renderer.context.error == "GL_NO_ERROR"
        report.update({"lamps": len(level.lighting.lights), "moving_frames": 60,
                       "gl_error": renderer.context.error})
        (output / "lighting-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))
    finally:
        if renderer is not None:
            renderer.release()
        pygame.quit()


if __name__ == "__main__":
    main()
