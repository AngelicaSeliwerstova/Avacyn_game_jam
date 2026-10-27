"""Зум на ПКМ в игровом цикле: геометрия, отсечение, снег и масштабирование."""

from collections import defaultdict
import json
import math
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame

from config import settings
from engine.rendering.renderer import Renderer
from engine.scene.box import Box
from engine.scene.interaction import Interaction
from engine.scene.level import Level
import main as game_main
from tools.check_rendering import expected_window, read_window, save_image


def check_application(render_size, output):
    level = Level((20, 20), 1, (
        Box((0, 1, 0), (1, 2, 1), emission=(3, 0, 0), interaction=Interaction("Crate", "Closed")),
        Box((2.8, 1, 0), (1, 2, 1), emission=(0, 0, 3)),
    ), (0, 1.6, 4), (0, 1.6, 3), ((60, 60, 60),) * 2)
    buttons = [False] * 5
    frames = 0
    measurements = {}

    class FixedClock:
        def tick(self, limit):
            return 1000 / 60

    class CheckedRenderer(Renderer):
        def render(self, window_size, hud_text="", debug_text="", *, aim_text=None):
            nonlocal frames
            super().render(window_size, hud_text, debug_text, aim_text=aim_text)
            frames += 1
            assert self.context.error == "GL_NO_ERROR"
            assert aim_text == "", "Zoom must not extend interaction reach"
            assert self._camera.position == (0, 1.6, 4)
            # Одна проекция нужна и геометрии, и частицам, включая промежуточный FOV.
            assert self._snow._program["m_projection"].read() == self._program["m_projection"].read()
            expected_scale = settings.SNOW_FLAKE_SIZE * render_size[1] / (
                2 * math.tan(math.radians(self._camera.fov_degrees) / 2))
            assert abs(self._snow._program["point_scale"].value - expected_scale) < 0.0001
            if frames in (2, 62):
                assert settings.CAMERA_ZOOM_FOV_DEGREES < self._camera.fov_degrees < settings.CAMERA_FOV_DEGREES
            if frames in (1, 61, 121):
                label = {1: "normal", 61: "zoomed", 121: "restored"}[frames]
                target = self.output_target
                data = target.framebuffer.read(components=3, alignment=1)
                width, height = target.size
                red_columns = [x for x in range(width) if any(
                    data[(y * width + x) * 3] > max(data[(y * width + x) * 3 + 1:
                                                       (y * width + x) * 3 + 3]) + 60
                    for y in range(height // 2 - 3, height // 2 + 3))]
                assert red_columns
                measurements[label] = {"fov": self._camera.fov_degrees,
                                       "object_width": max(red_columns) - min(red_columns) + 1,
                                       "submitted_boxes": self._submitted_objects}
                save_image(output / f"zoom-{label}-{width}.png", data, target.size)
                assert read_window(self, window_size) == expected_window(data, target.size, window_size)
                cx, cy = width // 2, height // 2
                assert data[(cy * width + cx) * 3:(cy * width + cx) * 3 + 3] == bytes((230, 228, 212))
            if frames == 1:
                buttons[2] = True
            if frames == 61:
                buttons[2] = False
            if frames == 121:
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    with patch.object(game_main, "create_level", return_value=level), \
            patch.object(settings, "RENDER_SIZE", render_size), \
            patch.object(settings, "DEBUG_ENABLED", False), \
            patch.object(settings, "TEXTURES_ENABLED", False), \
            patch.object(settings, "POSTPROCESS_ENABLED", False), \
            patch.object(settings, "SNOW_ENABLED", True), patch.object(settings, "SNOW_COUNT", 50), \
            patch.object(settings, "VSYNC", False), \
            patch("engine.core.application.Renderer", CheckedRenderer), \
            patch("pygame.time.Clock", return_value=FixedClock()), \
            patch("pygame.key.get_pressed", return_value=defaultdict(bool)), \
            patch("pygame.key.get_focused", return_value=True), \
            patch("pygame.mouse.get_rel", return_value=(0, 0)), \
            patch("pygame.mouse.get_pressed", side_effect=lambda count: tuple(buttons)), \
            patch("pygame.event.set_grab"), patch("pygame.mouse.set_visible"):
        game_main.main()
    normal, zoomed, restored = (measurements[key] for key in ("normal", "zoomed", "restored"))
    assert normal["fov"] == restored["fov"] == settings.CAMERA_FOV_DEGREES
    assert zoomed["fov"] == settings.CAMERA_ZOOM_FOV_DEGREES
    ratio = math.tan(math.radians(normal["fov"]) / 2) / math.tan(math.radians(zoomed["fov"]) / 2)
    assert abs(zoomed["object_width"] - normal["object_width"] * ratio) < 3
    assert normal["object_width"] == restored["object_width"]
    assert normal["submitted_boxes"] == restored["submitted_boxes"] == 2
    assert zoomed["submitted_boxes"] == 1, measurements
    return {"render_size": render_size, "frames": frames, **measurements,
            "snow_projection_matches": True, "reticle_unchanged": True,
            "interaction_reach_unchanged": True, "integer_scaling": True}


def main():
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    checks = [check_application(size, output) for size in ((640, 480), (320, 240))]
    report = {"checks": checks, "gl_error": "GL_NO_ERROR"}
    (output / "zoom-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
