"""GPU-проверки тумана, дальнего снега и синхронного мерцания ламп."""

from array import array
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import glm
import pygame

from config import settings
from engine.collision.aabb import AABB
from engine.core.window import Window
from engine.particles.snow import Snowfall, SnowSettings
from engine.rendering.fog import FogSettings
from engine.rendering.renderer import Renderer
from engine.rendering.snow import SnowRenderer
from engine.scene.box import Box
from engine.scene.camera import Camera
from engine.scene.level import Level
from engine.scene.lighting import LightFlicker, Lighting, PointLight
from game.effects import create_fog_settings, create_postprocess_settings
from game.levels import create_level
from game.materials import create_texture_settings
from game.ui import create_hud_style
from tools.check_rendering import save_image


SIZE = (640, 480)


def capture(renderer, window, text=""):
    renderer.render(window.size, hud_text=text)
    assert renderer.context.error == "GL_NO_ERROR"
    return renderer.output_target.framebuffer.read(components=3, alignment=1)


def sample(camera, pixels, point):
    clip = camera.projection_matrix(SIZE[0] / SIZE[1]) * camera.view_matrix * glm.vec4(*point, 1)
    px, py = (int((clip[i] / clip.w * 0.5 + 0.5) * SIZE[i]) for i in range(2))
    assert 1 <= px < SIZE[0] - 1 and 1 <= py < SIZE[1] - 1, (point, px, py)
    values = [pixels[(y * SIZE[0] + x) * 3:(y * SIZE[0] + x) * 3 + 3]
              for y in range(py - 1, py + 2) for x in range(px - 1, px + 2)]
    return tuple(round(sum(value[c] for value in values) / len(values)) for c in range(3))


def check_fog(window, output):
    fog = FogSettings((0.2, 0.3, 0.4), 6, 16)
    level = Level((60, 60), 1, (), (0, 5, 10), (0, 0, 0), ((200, 200, 200),) * 2)
    camera = Camera(level.spawn_position, level.spawn_target, 80, 0.1, 100)
    renderer = Renderer(SIZE, (0, 0, 0), settings.OPENGL_VERSION, camera, level, fog=fog)
    snow_renderer = None
    try:
        renderer._program["fog_enabled"].value = False
        plain = capture(renderer, window, "FOG TEST")
        renderer._program["fog_enabled"].value = True
        texture = renderer._hud._texture
        fogged = capture(renderer, window, "FOG TEST")
        assert renderer._hud._texture is texture
        points = ((0, 0, 7), (0, 0, 0), (0, 0, -12))
        colors = [sample(camera, fogged, point) for point in points]
        for point, actual in zip(points, colors):
            original = sample(camera, plain, point)
            distance = glm.length(glm.vec3(point) - camera.position)
            t = max(0, min(1, (distance - fog.start) / (fog.end - fog.start)))
            factor = t * t * (3 - 2 * t)
            expected = tuple(round(c * (1 - factor) + f * 255 * factor) for c, f in zip(original, fog.color))
            assert max(abs(a - b) for a, b in zip(actual, expected)) <= 2, (point, actual, expected)
        assert colors[0] == sample(camera, plain, points[0])
        text_color = bytes((230, 228, 212))
        glyphs = [i for i in range(0, len(plain), 3) if plain[i:i + 3] == text_color]
        assert len(glyphs) > 20 and all(fogged[i:i + 3] == text_color for i in glyphs)
        save_image(output / "fog-probes.png", fogged, SIZE)

        # Все частицы дальше конца тумана: их цвет должен совпасть с фоном.
        snow = Snowfall(SnowSettings(50, 5, 0.5, 0.5, (255, 255, 255), 7), AABB(-2, -16, 2, -12), ())
        snow_renderer = SnowRenderer(renderer.context, snow, camera, SIZE, fog=fog)
        renderer._snow = snow_renderer
        distant = capture(renderer, window, "FOG TEST")
        assert max(abs(a - b) for a, b in zip(distant, fogged)) <= 1
        renderer._program["fog_enabled"].value = False
        snow_renderer._program["fog_enabled"].value = False
        visible = capture(renderer, window, "FOG TEST")
        assert sum(a != b for a, b in zip(visible, plain)) > 100
        return {"near_rgb": colors[0], "middle_rgb": colors[1], "far_rgb": colors[2],
                "hud_unaffected": True, "distant_snow_fades": True}
    finally:
        renderer._snow = None
        if snow_renderer is not None:
            snow_renderer.release()
        renderer.release()


def check_flicker(window, output):
    effect = LightFlicker()
    panel = Box((-2, 3.1, 0), (0.9, 0.05, 0.5), emission=(0.7, 0.8, 1), emission_light=0)
    level = Level((20, 20), 1, (Box((0, 1, 0), (0.25, 2, 6)),),
                  (0, 4.5, 8), (0, 1, 0), ((200, 200, 200),) * 2,
                  lighting=Lighting((0.04, 0.04, 0.04), (
                      PointLight((-2, 3, 0), (0.6, 0.8, 1), 3, 4.5, flicker=effect),
                      PointLight((4, 3, 0), (0.8, 0.5, 0.25), 3, 4.5),
                  )), decorations=(panel,))
    camera = Camera(level.spawn_position, level.spawn_target, 70, 0.1, 100)
    renderer = Renderer(SIZE, (0, 0, 0), settings.OPENGL_VERSION, camera, level)
    try:
        renderer.update(2)
        bright = capture(renderer, window)
        atlas = renderer._lighting._texture
        shadow_hash = hashlib.sha256(atlas.read()).digest()
        initial_data = renderer._lighting._light_data.read()
        dark_time = 8 + min(range(4800), key=lambda i: effect.brightness(i / 600)) / 600
        renderer.update(dark_time - 2)
        dim = capture(renderer, window)
        changed_data = renderer._lighting._light_data.read()
        assert initial_data[:32] == changed_data[:32], "Positions and radii must remain static"
        a, b = array("f", initial_data), array("f", changed_data)
        assert a[12:16] == b[12:16], "Steady lamp data must remain unchanged"
        assert b[11] < a[11] * 0.31
        assert renderer._lighting._texture is atlas
        assert shadow_hash == hashlib.sha256(atlas.read()).digest(), "Flicker must reuse shadow maps"
        floor_lit, floor_dim = (sample(camera, pixels, (-2, 0, 0)) for pixels in (bright, dim))
        panel_lit, panel_dim = (sample(camera, pixels, (-2, 3.125, 0)) for pixels in (bright, dim))
        assert floor_lit[2] > floor_dim[2] + 30, (floor_lit, floor_dim)
        assert panel_lit[2] > panel_dim[2] + 80, (panel_lit, panel_dim)
        assert sample(camera, bright, (4, 0, 0)) == sample(camera, dim, (4, 0, 0))
        save_image(output / "flicker-bright.png", bright, SIZE)
        save_image(output / "flicker-dim.png", dim, SIZE)
        renderer.options = replace(renderer.options, light_flicker=False)
        renderer.update(0)
        assert capture(renderer, window) == bright
        return {"floor_bright_rgb": floor_lit, "floor_dim_rgb": floor_dim,
                "panel_bright_rgb": panel_lit, "panel_dim_rgb": panel_dim,
                "steady_lamp_unchanged": True, "shadow_atlas_unchanged": True,
                "disable_restores_original": True}
    finally:
        renderer.release()


def capture_levels(window, output):
    for name in ("maze", "corridor"):
        level = create_level(name)
        position, target = ((-28, -2, 17.5), (-25, -2.5, 13.8)) if name == "maze" else (
            level.spawn_position, level.spawn_target)
        camera = Camera(position, target, settings.CAMERA_FOV_DEGREES, settings.CAMERA_NEAR, settings.CAMERA_FAR)
        snow = None
        if level.snow_enabled:
            snow = Snowfall(SnowSettings(600, 5, 0.65, 0.05, (210, 220, 235), 7),
                            level.floor_bounds, tuple(b.footprint for b in level.boxes))
        renderer = Renderer(SIZE, settings.BACKGROUND_COLOR, settings.OPENGL_VERSION, camera, level,
                            snow=snow, textures=create_texture_settings(), postprocess=create_postprocess_settings(),
                            hud_style=create_hud_style(), fog=create_fog_settings())
        try:
            for _ in range(120):
                renderer.update(1 / 60)
                if snow is not None:
                    snow.update(1 / 60)
                renderer.render(window.size)
            pixels = capture(renderer, window, "FLOOR B1" if name == "maze" else "CORRIDOR")
            save_image(output / f"fog-{name}.png", pixels, SIZE)
        finally:
            renderer.release()


def main():
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    pygame.init()
    try:
        window = Window(settings.WINDOW_SIZE, "Atmosphere check", settings.OPENGL_VERSION, False, SIZE)
        report = {"fog": check_fog(window, output), "flicker": check_flicker(window, output)}
        capture_levels(window, output)
        report.update({"level_frames": 240, "gl_error": "GL_NO_ERROR"})
        (output / "atmosphere-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
