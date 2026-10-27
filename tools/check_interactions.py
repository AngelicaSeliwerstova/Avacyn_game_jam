"""Настоящий игровой цикл: наведение на коробку, E, удержание и ответ на GPU."""

from collections import defaultdict
from dataclasses import replace
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame

from config import settings
from engine.input.keyboard_mouse import KeyboardMouse
from engine.rendering.renderer import Renderer
from game.levels import create_level
import main as game_main
from tools.check_rendering import expected_window, read_window, save_image


def check_application(render_size, output):
    level = create_level("maze")
    y = level.base_height + settings.PLAYER_EYE_HEIGHT
    level = replace(level, spawn_position=(-27, y, 13.8), spawn_target=(-25, y, 13.8))
    frames, presses = 0, 0
    keys, checks = defaultdict(bool), {}
    motion = (0, 0)

    def read_motion():
        nonlocal motion
        result, motion = motion, (0, 0)
        return result

    class FixedClock:
        # Чтение GPU-кадров для проверки не должно менять время жизни сообщения.
        def tick(self, limit):
            return 1000 / 60

    class CheckedInput(KeyboardMouse):
        def read(self):
            nonlocal presses
            state = super().read()
            presses += state.interact
            return state

    class CheckedRenderer(Renderer):
        def render(self, window_size, hud_text="", debug_text="", *, aim_text=None):
            nonlocal frames, motion
            overlay = self._aim_hud._text
            old_text, old_texture = overlay._text, overlay._texture
            super().render(window_size, hud_text, debug_text, aim_text=aim_text)
            frames += 1
            assert self.context.error == "GL_NO_ERROR"
            if aim_text and old_text == aim_text:
                assert overlay._texture is old_texture
                checks["cached_prompt"] = True
            if frames == 1:
                assert "[E] Inspect - Small wooden crate" in aim_text, aim_text
                keys[pygame.K_e] = True
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
                checks["actual_basement_crate_targeted"] = True
            if frames == 2:
                assert "Something rattles inside." in aim_text, aim_text
            if frames == 5:
                target = self.output_target
                pixels = target.framebuffer.read(components=3, alignment=1)
                save_image(output / f"interaction-{render_size[0]}.png", pixels, target.size)
                assert read_window(self, window_size) == expected_window(pixels, target.size, window_size)
                width, height = target.size
                index = ((height // 2) * width + width // 2) * 3
                assert pixels[index:index + 3] == bytes((230, 228, 212))
                panel_width, panel_height = overlay._texture.size
                margin = overlay._style.margin
                assert panel_width <= width - 2 * margin
                left = (width - panel_width) // 2
                super().render(window_size, hud_text, debug_text)
                plain = target.framebuffer.read(components=3, alignment=1)
                assert plain != pixels
                for py in range(height):
                    for px in range(width):
                        if (left <= px < left + panel_width and margin <= py < margin + panel_height
                                or width // 2 - 2 <= px < width // 2 + 2
                                and height // 2 - 2 <= py < height // 2 + 2):
                            continue
                        offset = (py * width + px) * 3
                        assert pixels[offset:offset + 3] == plain[offset:offset + 3]
                super().render(window_size, hud_text, debug_text, aim_text=aim_text)
                checks.update({"integer_scaling": True, "reticle_at_center": True,
                               "outside_overlay_unchanged": True})
            if 2 <= frames <= 20:
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=True))
            if frames == 10:
                motion = (750, 0)
            if frames == 11:
                assert "[E]" not in aim_text and "Something rattles inside." in aim_text
                checks["look_away_removes_prompt"] = True
            if frames == 25:
                assert aim_text == "", aim_text
                assert presses == 1, presses
                checks["held_key_does_not_repeat_or_extend_message"] = True
                motion = (-750, 0)
                pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_e))
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
            if frames == 26:
                assert "[E]" in aim_text and "Something rattles inside." in aim_text
                checks["second_press_works"] = True
                long_text = aim_text + "\n" + "A long inspection message should wrap inside the frame. " * 2
                super().render(window_size, hud_text, debug_text, aim_text=long_text)
                assert overlay._texture.width <= render_size[0] - 2 * overlay._style.margin
                assert overlay._texture.height < render_size[1]
                save_image(output / f"interaction-wrapped-{render_size[0]}.png",
                           self.output_target.framebuffer.read(components=3, alignment=1), render_size)
                super().render(window_size, hud_text, debug_text, aim_text=aim_text)
                checks["long_message_wraps"] = True
            if frames == 30:
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    with patch.object(game_main, "create_level", return_value=level), \
            patch.object(settings, "RENDER_SIZE", render_size), \
            patch.object(settings, "DEBUG_ENABLED", False), \
            patch.object(settings, "INTERACTION_MESSAGE_SECONDS", 0.25), \
            patch("engine.core.application.KeyboardMouse", CheckedInput), \
            patch("engine.core.application.Renderer", CheckedRenderer), \
            patch("pygame.time.Clock", return_value=FixedClock()), \
            patch("pygame.key.get_pressed", return_value=keys), \
            patch("pygame.key.get_focused", return_value=True), \
            patch("pygame.mouse.get_rel", side_effect=read_motion), \
            patch("pygame.mouse.get_pressed", return_value=(False,) * 5), \
            patch("pygame.event.set_grab"), patch("pygame.mouse.set_visible"):
        game_main.main()
    assert frames == 30 and presses == 2, (frames, presses)
    return {"render_size": render_size, "frames": frames, "action_presses": presses, **checks}


def main():
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    checks = [check_application(size, output) for size in ((640, 480), (320, 240))]
    report = {"checks": checks, "gl_error": "GL_NO_ERROR"}
    (output / "interaction-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
