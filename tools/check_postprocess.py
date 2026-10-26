"""Проверка холодного оттенка, ореолов, чётких пикселей и HUD на GPU."""

from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import moderngl
import pygame

from config import settings
from engine.core.window import Window
from engine.rendering.postprocess import PostProcessor
from engine.rendering.renderer import Renderer
from engine.scene.camera import Camera
from game.effects import create_postprocess_settings
from game.levels import create_level
from game.materials import create_texture_settings
from tools.check_rendering import expected_window, read_window, save_image


def check_effects(context, style):
    size = (64, 48)
    source = context.texture(size, 4)
    source.filter = moderngl.NEAREST, moderngl.NEAREST
    source.repeat_x = source.repeat_y = False
    effects = []
    try:
        neutral = PostProcessor(context, size, replace(style, strength=0, bloom_strength=0))
        effects.append(neutral)
        original = bytes(channel for y in range(size[1]) for x in range(size[0])
                         for channel in (x * 4, y * 5, (x + y) % 256, 255))
        source.write(original)
        output = neutral.apply(source).framebuffer.read(components=4, alignment=1)
        assert output == original, "Zero effect strengths must preserve each pixel"
        assert neutral.apply(source).framebuffer.read(components=4, alignment=1) == output

        cold = PostProcessor(context, size, style)
        effects.append(cold)
        source.write(bytes((128, 128, 128, 255)) * (size[0] * size[1]))
        gray = cold.apply(source).framebuffer.read(components=4, alignment=1)
        r, g, b = gray[:3]
        assert b > g > r, (r, g, b)

        glow = PostProcessor(context, size, replace(style, strength=0, bloom_strength=1,
                                                   bloom_threshold=0.6, downsample=2))
        effects.append(glow)
        spot = bytearray(bytes((0, 0, 0, 255)) * (size[0] * size[1]))
        for y in range(20, 28):
            for x in range(28, 36):
                offset = (y * size[0] + x) * 4
                spot[offset:offset + 4] = bytes((255, 255, 255, 255))
        source.write(spot)
        halo = glow.apply(source).framebuffer.read(components=4, alignment=1)
        blue_halo_pixels = 0
        for y in range(size[1]):
            for x in range(size[0]):
                offset = (y * size[0] + x) * 4
                rgb = halo[offset:offset + 3]
                if not (28 <= x < 36 and 20 <= y < 28) and rgb[2] > rgb[0]:
                    blue_halo_pixels += 1
                if x in (0, size[0] - 1) or y in (0, size[1] - 1):
                    assert rgb == bytes((0, 0, 0)), "Bloom must not wrap around image edges"
        assert blue_halo_pixels > 20, blue_halo_pixels
        assert source.read() == spot, "Postprocessing must not overwrite the scene"
        assert context.error == "GL_NO_ERROR"
        return {"zero_strength_identity": True, "neutral_gray_after": [r, g, b],
                "blue_halo_pixels": blue_halo_pixels, "scene_preserved": True}
    finally:
        for effect in effects:
            effect.release()
        source.release()


def main():
    renderer = None
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    pygame.init()
    try:
        window = Window(settings.WINDOW_SIZE, "Cold glow check", settings.OPENGL_VERSION,
                        settings.VSYNC, settings.RENDER_SIZE)
        level = create_level(settings.LEVEL_NAME)
        camera = Camera(level.spawn_position, level.spawn_target, settings.CAMERA_FOV_DEGREES,
                        settings.CAMERA_NEAR, settings.CAMERA_FAR)
        style = create_postprocess_settings()
        assert style is not None
        renderer = Renderer(settings.RENDER_SIZE, settings.BACKGROUND_COLOR, settings.OPENGL_VERSION,
                            camera, level, textures=create_texture_settings(), postprocess=style)
        report = check_effects(renderer.context, style)
        renderer.render(window.size)
        before = renderer._render_target.framebuffer.read(components=3, alignment=1)
        after = renderer.output_target.framebuffer.read(components=3, alignment=1)
        assert before != after
        save_image(output / "cold-before.png", before, settings.RENDER_SIZE)
        save_image(output / "cold-after.png", after, settings.RENDER_SIZE)
        renderer.render(window.size)
        assert after == renderer.output_target.framebuffer.read(components=3, alignment=1)

        # HUD рисуется после эффекта: непрозрачные пиксели букв сохраняют исходный цвет.
        renderer.render(window.size, hud_text="FLOOR 1 / 2\nFind stairs. Exit is upstairs.")
        hud = renderer._hud
        hud_pixels = hud._texture.read(alignment=1)
        glyph_offset = next(i for i in range(0, len(hud_pixels), 4)
                            if hud_pixels[i:i + 4] == bytes((230, 228, 212, 255)))
        column = (glyph_offset // 4) % hud._texture.width
        row = (glyph_offset // 4) // hud._texture.width
        x = hud._style.margin + column
        y = settings.RENDER_SIZE[1] - hud._texture.height - hud._style.margin + row
        pixels = renderer.output_target.framebuffer.read(components=4, alignment=1)
        offset = (y * settings.RENDER_SIZE[0] + x) * 4
        assert pixels[offset:offset + 3] == bytes((230, 228, 212))

        window._native_window.size = (1001, 777)
        window.handle_event(pygame.event.Event(pygame.WINDOWSIZECHANGED))
        renderer.render(window.size)
        target = renderer.output_target
        frame = target.framebuffer.read(components=3, alignment=1)
        assert read_window(renderer, window.size) == expected_window(frame, target.size, window.size)
        assert renderer.context.error == "GL_NO_ERROR"
        report.update({"stable_frames": True, "hud_color_preserved": True,
                       "integer_scaling_and_black_bars": True, "gl_error": renderer.context.error})
        (output / "cold-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))
    finally:
        if renderer is not None:
            renderer.release()
        pygame.quit()


if __name__ == "__main__":
    main()
