"""Проверка настоящего GPU-кадра: каждый пиксель, поля и смена режима окна."""

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame

from config import settings
from engine.core.window import Window
from engine.rendering.presentation import integer_viewport
from engine.rendering.renderer import Renderer
from engine.scene.camera import Camera
from game.levels import create_level


def read_window(renderer, size):
    context = renderer.context
    # ModernGL хранит исходный размер screen. После resize определяем
    # framebuffer 0 заново при viewport, равном реальному размеру окна.
    context.screen.use()
    context.viewport = (0, 0, *size)
    screen = context.detect_framebuffer(0)
    capture = context.simple_framebuffer(size, components=3)
    try:
        context.copy_framebuffer(capture, screen)
        return capture.read(components=3, alignment=1)
    finally:
        capture.release()
        context.screen.use()
        screen.release()


def expected_window(pixels, render_size, window_size):
    width, height = window_size
    render_width, render_height = render_size
    x, y, scaled_width, _ = integer_viewport(window_size, render_size)
    scale = scaled_width // render_width
    result = bytearray(width * height * 3)
    for row in range(render_height):
        source = pixels[row * render_width * 3:(row + 1) * render_width * 3]
        expanded = b"".join(source[i:i + 3] * scale for i in range(0, len(source), 3))
        for repeat in range(scale):
            offset = ((y + row * scale + repeat) * width + x) * 3
            result[offset:offset + len(expanded)] = expanded
    return bytes(result)


def save_image(path, pixels, size):
    surface = pygame.image.frombytes(pixels, size, "RGB")
    pygame.image.save(pygame.transform.flip(surface, False, True), path)


def main():
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    renderer = None
    pygame.init()
    try:
        level = create_level(settings.LEVEL_NAME)
        camera = Camera(
            level.spawn_position, level.spawn_target, settings.CAMERA_FOV_DEGREES,
            settings.CAMERA_NEAR, settings.CAMERA_FAR,
        )
        window = Window(
            settings.WINDOW_SIZE, "gamek | GPU check", settings.OPENGL_VERSION,
            settings.VSYNC, minimum_size=settings.RENDER_SIZE,
        )
        renderer = Renderer(
            render_size=settings.RENDER_SIZE, background_color=settings.BACKGROUND_COLOR,
            opengl_version=settings.OPENGL_VERSION, camera=camera, level=level,
        )
        framebuffer_id = renderer._render_target.framebuffer.glo
        baseline = None
        cases = []

        def check(name):
            nonlocal baseline
            for _ in range(2):
                for event in pygame.event.get():
                    window.handle_event(event)
            size = window.size
            renderer.render(size)
            target = renderer._render_target
            assert target.size == settings.RENDER_SIZE
            assert target.framebuffer.glo == framebuffer_id
            low_pixels = target.framebuffer.read(components=3, alignment=1)
            if baseline is None:
                baseline = low_pixels
                save_image(output / "step08-internal.png", low_pixels, target.size)
            assert low_pixels == baseline, f"Projection or scene changed in {name}"
            actual = read_window(renderer, size)
            expected = expected_window(low_pixels, target.size, size)
            assert actual == expected, f"Pixel scaling or bars differ in {name}: {size}"
            assert renderer.context.error == "GL_NO_ERROR"
            if name in ("default", "odd_size", "fullscreen"):
                save_image(output / f"step08-{name}.png", actual, size)
            cases.append({"case": name, "window": size, "viewport": integer_viewport(size, target.size)})
            pygame.display.flip()
            print(f"PASS: {name}, window={size}, every RGB pixel matches")

        check("default")
        for name, requested in (
            ("odd_size", (1001, 777)),
            ("widescreen", (960, 540)),
            ("minimum", (200, 100)),
        ):
            window._native_window.size = requested
            window.handle_event(pygame.event.Event(pygame.WINDOWSIZECHANGED))
            check(name)
            if name == "minimum":
                assert window.size == settings.RENDER_SIZE

        window._native_window.size = (1001, 777)
        check("before_fullscreen")
        window.toggle_fullscreen()
        check("fullscreen")
        window.toggle_fullscreen()
        check("restored")
        assert window.size == (1001, 777)
        report = {
            "status": "passed", "render_size": settings.RENDER_SIZE, "cases": cases,
            "opengl": {key: renderer.context.info[key] for key in ("GL_VENDOR", "GL_RENDERER", "GL_VERSION")},
        }
        (output / "step08-check.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8",
        )
    finally:
        try:
            if renderer is not None:
                renderer.release()
        finally:
            pygame.quit()


if __name__ == "__main__":
    main()
