"""Запускает настоящий игровой цикл, проверяет F3, кэш текста и панель на GPU."""

from collections import defaultdict
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame

from config import settings
from engine.core.application import Application
from engine.input.keyboard_mouse import KeyboardMouse
from engine.rendering.renderer import Renderer
import main as game_main
from tools.check_rendering import expected_window, read_window, save_image


class ScriptedInput(KeyboardMouse):
    # Проверка не захватывает системный курсор; события и чтение клавиш остаются настоящими.
    def _set_capture(self, captured):
        self._captured = captured
        self._discard_mouse_delta = True
        self._jump_queued = self._jump_held = False


def check_application(render_size, initially_enabled, output):
    application = None
    frames = 0
    keys = defaultdict(bool)
    checks = {}

    def create_application(*args, **kwargs):
        nonlocal application
        application = Application(*args, **kwargs)
        return application

    class CheckedRenderer(Renderer):
        def render(self, window_size, hud_text="", debug_text=""):
            nonlocal frames
            old_text, old_texture = self._debug_hud._text, self._debug_hud._texture
            super().render(window_size, hud_text, debug_text)
            frames += 1
            assert self.context.error == "GL_NO_ERROR"
            if debug_text and old_text == debug_text:
                assert self._debug_hud._texture is old_texture
                checks["cached_text"] = True
            if frames == 1:
                if not initially_enabled:
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F3))
            if frames == 4:
                assert debug_text
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F3, repeat=True))
            if frames == 5:
                assert debug_text, "Key repeat must not hide the panel"
                checks["repeat_ignored"] = True
            if frames == 10:
                keys[pygame.K_w] = True
            if frames == 20:
                keys[pygame.K_w] = False
            if frames == 30:
                assert "FPS: " in debug_text and "FPS: ..." not in debug_text
                assert "FEET XYZ:" in debug_text and "SCENE:" in debug_text
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F3))
            if frames == 31:
                assert not debug_text
                checks["hidden"] = True
                pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_F3))
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F3))
            if frames == 40:
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
            if frames == 65:
                assert "INPUT: CURSOR FREE" in debug_text
                assert "SIM: RUNNING" in debug_text
                target = self.output_target
                panel = self._debug_hud._texture
                assert panel.width + 2 * self._debug_hud._style.margin <= target.size[0], panel.size
                assert panel.height + 2 * self._debug_hud._style.margin <= target.size[1], panel.size
                with_debug = target.framebuffer.read(components=3, alignment=1)
                assert read_window(self, window_size) == expected_window(with_debug, target.size, window_size)
                save_image(output / f"debug-{render_size[0]}.png", with_debug, target.size)
                super().render(window_size, hud_text, "")
                without_debug = target.framebuffer.read(components=3, alignment=1)
                assert with_debug != without_debug
                # Вне прямоугольника панели изображение совпадает побайтно.
                margin = self._debug_hud._style.margin
                left, right = target.size[0] - panel.width - margin, target.size[0] - margin
                for y in range(target.size[1]):
                    for x in range(target.size[0]):
                        if left <= x < right and margin <= y < margin + panel.height:
                            continue
                        offset = (y * target.size[0] + x) * 3
                        assert with_debug[offset:offset + 3] == without_debug[offset:offset + 3]
                checks.update({"panel_size": panel.size, "outside_panel_unchanged": True,
                               "integer_scaling": True, "cursor_free_is_not_pause": True})
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    with patch.object(settings, "RENDER_SIZE", render_size), patch.object(settings, "DEBUG_ENABLED", initially_enabled), \
            patch.object(game_main, "Application", side_effect=create_application), \
            patch("engine.core.application.Renderer", CheckedRenderer), \
            patch("engine.core.application.KeyboardMouse", ScriptedInput), \
            patch("pygame.key.get_focused", return_value=True), \
            patch("pygame.key.get_pressed", return_value=keys), \
            patch("pygame.mouse.get_rel", return_value=(0, 0)):
        game_main.main()
    assert not application._running
    assert frames == 65, frames
    assert application._debug.enabled
    return {"render_size": render_size, "initially_enabled": initially_enabled, "frames": frames, **checks}


def main():
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    checks = [check_application((640, 480), False, output), check_application((320, 240), True, output)]
    report = {"checks": checks, "gl_error": "GL_NO_ERROR"}
    (output / "debug-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
