"""Проверяет настоящие GPU-фильтры, mip-уровни и движение мелкого рисунка."""

import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import glm
import moderngl
import pygame

from config import settings
from engine.core.window import Window
from engine.rendering.renderer import Renderer
from engine.rendering.texture import Texture2D
from engine.scene.camera import Camera
from game.levels import create_level
from game.materials import create_texture_settings
from tools.check_rendering import expected_window, read_window, save_image


def check_sampler(context, directory):
    path = Path(directory) / "checker.png"
    image = pygame.Surface((128, 128))
    for y in range(128):
        for x in range(128):
            value = 255 if (x + y) % 2 else 0
            image.set_at((x, y), (value,) * 3)
    pygame.image.save(image, str(path))
    textures = []
    program = context.program(
        vertex_shader="""#version 330
        uniform vec2 uv_scale;
        uniform vec2 uv_offset;
        out vec2 uv;
        void main() {
            vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
            uv = p * uv_scale + uv_offset;
            gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
        }""",
        fragment_shader="""#version 330
        uniform sampler2D source;
        in vec2 uv;
        out vec4 color;
        void main() { color = vec4(texture(source, uv).rgb, 1.0); }
        """,
    )
    vertices = context.vertex_array(program, [])
    target = context.simple_framebuffer((128, 128), components=3)
    try:
        filtered = Texture2D(context, path, True, settings.TEXTURE_ANISOTROPY)
        textures.append(filtered)
        raw = Texture2D(context, path, False, settings.TEXTURE_ANISOTROPY)
        textures.append(raw)
        assert filtered.texture.filter == (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.NEAREST)
        assert filtered.levels == 8
        for level in range(8):
            side = max(1, 128 >> level)
            assert len(filtered.texture.read(level=level, alignment=1)) == side * side * 3
        smallest = filtered.texture.read(level=7, alignment=1)
        assert all(127 <= c <= 128 for c in smallest)
        # Нечётный размер проверяет выравнивание RGB-строк и полную цепочку mipmaps.
        npot_image = pygame.Surface((7, 5))
        npot_image.fill((0, 255, 0))
        npot_image.fill((255, 0, 0), (0, 0, 7, 1))
        npot_image.fill((0, 0, 255), (0, 4, 7, 1))
        npot_path = Path(directory) / "npot.png"
        pygame.image.save(npot_image, str(npot_path))
        npot = Texture2D(context, npot_path, True, settings.TEXTURE_ANISOTROPY)
        textures.append(npot)
        assert npot.levels == 3
        assert [len(npot.texture.read(level=i, alignment=1)) for i in range(3)] == [105, 18, 3]
        assert npot.texture.read(alignment=1)[:3] == bytes((0, 0, 255)), "PNG must be flipped for OpenGL"
        target.use()
        context.viewport = (0, 0, 128, 128)
        context.disable(moderngl.DEPTH_TEST | moderngl.BLEND)
        program["source"].value = 0

        def capture(texture, scale, offset):
            texture.use()
            program["uv_scale"].value = (scale, scale)
            program["uv_offset"].value = (offset, 0)
            vertices.render(mode=moderngl.TRIANGLES, vertices=3)
            return target.read(components=3, alignment=1)

        close = capture(filtered, 0.125, 0)
        assert set(close) == {0, 255}, "Magnification must retain crisp, unmixed texels"
        changes = {}
        for name, texture in (("mipmaps", filtered), ("nearest_only", raw)):
            frames = [capture(texture, 32, frame / (4 * 128)) for frame in range(16)]
            changes[name] = sum(
                sum(abs(a - b) for a, b in zip(before, after)) / len(before)
                for before, after in zip(frames, frames[1:])
            ) / (len(frames) - 1)
        assert changes["nearest_only"] > 10, changes
        assert changes["mipmaps"] < changes["nearest_only"] * 0.05, changes
        assert context.error == "GL_NO_ERROR"
        return {"levels": 8, "crisp_magnification": True, "npot_and_orientation": True,
                "temporal_change": changes}
    finally:
        for texture in textures:
            texture.release()
        target.release()
        vertices.release()
        program.release()


def main():
    renderer = None
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    pygame.init()
    try:
        window = Window(settings.WINDOW_SIZE, "Texture check", settings.OPENGL_VERSION,
                        settings.VSYNC, settings.RENDER_SIZE)
        level = create_level(settings.LEVEL_NAME)
        camera = Camera(level.spawn_position, level.spawn_target, settings.CAMERA_FOV_DEGREES,
                        settings.CAMERA_NEAR, settings.CAMERA_FAR)
        material_settings = create_texture_settings()
        assert material_settings is not None
        renderer = Renderer(settings.RENDER_SIZE, settings.BACKGROUND_COLOR,
                            settings.OPENGL_VERSION, camera, level, textures=material_settings)
        with tempfile.TemporaryDirectory() as directory:
            report = check_sampler(renderer.context, directory)
        renderer.render(window.size)
        target = renderer._render_target
        initial = target.framebuffer.read(components=3, alignment=1)
        assert read_window(renderer, window.size) == expected_window(initial, target.size, window.size)
        save_image(output / "textures-start.png", initial, target.size)
        renderer.render(window.size)
        assert initial == target.framebuffer.read(components=3, alignment=1)
        for _ in range(60):
            pygame.event.pump()
            camera.position += glm.vec3(0, 0, -0.01)
            camera.target += glm.vec3(0, 0, -0.01)
            renderer.render(window.size)
            assert renderer.context.error == "GL_NO_ERROR"
            window.present()
        moved = target.framebuffer.read(components=3, alignment=1)
        assert initial != moved
        save_image(output / "textures-moved.png", moved, target.size)
        report.update({"world_motion_frames": 60, "integer_scaling": True, "gl_error": renderer.context.error})
        (output / "textures-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))
    finally:
        if renderer is not None:
            renderer.release()
        pygame.quit()


if __name__ == "__main__":
    main()
