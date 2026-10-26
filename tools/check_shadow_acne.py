"""Проверяет полосы самозатенения на ровной стене под скользящим светом."""

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
from tools.check_rendering import save_image


def check_wall(window, resolution, angle, light_height, output):
    rotation = glm.rotate(glm.mat4(1), glm.radians(angle), glm.vec3(0, 1, 0))

    def rotate(point):
        return tuple(glm.vec3(rotation * glm.vec4(*point, 1)))

    wall_size = (16, 6, 0.4) if angle % 180 == 0 else (0.4, 6, 16)
    light = PointLight(rotate((0, light_height, 0.4)), (1, 1, 1), 4, 14)
    wall = Box(rotate((0, 3, -0.2)), wall_size)
    camera = Camera(rotate((1.8, 2.3, 4)), rotate((0, 3, 0)), 80, 0.1, 100)
    level = Level((20, 20), 1, (wall,), tuple(camera.position), tuple(camera.target),
                  ((160, 160, 160),) * 2,
                  lighting=Lighting((0.15, 0.15, 0.15), (light,), resolution))
    renderer = Renderer((320, 240), (0, 0, 0), settings.OPENGL_VERSION, camera, level)
    white = None
    try:
        def draw():
            renderer.render(window.size)
            return renderer.output_target.framebuffer.read(components=3, alignment=1)

        white = renderer.context.texture((1, 1), 1, array("f", [1.0]).tobytes(), dtype="f4")
        atlas = renderer._lighting._texture
        max_error = 0
        affected = 0
        sampled = 0
        for frame in range(5):
            camera.position.x += 0.013
            camera.target.x += 0.013
            actual = draw()
            renderer._lighting._texture = white
            try:
                expected = draw()
            finally:
                renderer._lighting._texture = atlas
            # Внутренняя часть стены: у границ геометрии PCF может давать настоящую полутень.
            mask = pygame.Surface((320, 240))
            corners = []
            matrix = camera.projection_matrix(320 / 240) * camera.view_matrix
            for point in ((-6.5, 0.8, 0), (6.5, 0.8, 0), (6.5, 5.2, 0), (-6.5, 5.2, 0)):
                clip = matrix * glm.vec4(*rotate(point), 1)
                corners.append(((clip.x / clip.w * 0.5 + 0.5) * 320,
                                (clip.y / clip.w * 0.5 + 0.5) * 240))
            pygame.draw.polygon(mask, (255, 255, 255), corners)
            mask_pixels = pygame.image.tobytes(mask, "RGB")
            errors = [abs(a - b) for a, b, selected in zip(actual, expected, mask_pixels) if selected]
            sampled += len(errors)
            max_error = max(max_error, max(errors))
            affected += sum(error > 1 for error in errors)
            if resolution == 128 and angle == 0 and light_height == 5.5 and frame == 0:
                target = renderer.output_target
                save_image(output / "shadow-wall-actual.png", actual, target.size)
                save_image(output / "shadow-wall-reference.png", expected, target.size)
        assert renderer.context.error == "GL_NO_ERROR"
        assert sampled > 100000, sampled
        assert max_error <= 1, (resolution, angle, light_height, max_error, affected)
        return {"resolution": resolution, "angle": angle, "light_height": light_height,
                "max_channel_error": max_error, "affected_channels": affected,
                "checked_channels": sampled, "frames": 5}
    finally:
        if white is not None:
            white.release()
        renderer.release()


def main():
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    pygame.init()
    try:
        window = Window(settings.WINDOW_SIZE, "Shadow acne check", settings.OPENGL_VERSION,
                        settings.VSYNC, settings.RENDER_SIZE)
        checks = [check_wall(window, resolution, angle, height, output)
                  for resolution in (128, 64, 256) for angle in (0, 90, 180, 270) for height in (5.5, 0.5)]
        report = {"wall_checks": checks, "gl_error": "GL_NO_ERROR"}
        (output / "shadow-acne-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"cases": len(checks), "frames": sum(c["frames"] for c in checks),
                          "max_channel_error": max(c["max_channel_error"] for c in checks),
                          "checked_channels": sum(c["checked_channels"] for c in checks),
                          "gl_error": report["gl_error"]}))
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
