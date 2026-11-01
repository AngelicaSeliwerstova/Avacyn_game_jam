"""Capture the closed cabinet and open 1981 drawer with the real game renderer."""

from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from config import settings
from engine.rendering.renderer import Renderer
from engine.scene.camera import Camera
from game.levels.patient_archive import ARCHIVE_DRAWER_ID
from game.levels.story_props import StoryPropSystem
from main import run_session


def capture():
    output = Path("artifacts/patient-archive-qa")
    output.mkdir(parents=True, exist_ok=True)
    original_mode, original_render = pygame.display.set_mode, Renderer.render
    views = (
        ("cabinet-closed", (10.6, 1.9, 4.4), (10.6, 1.5, 0.8)),
        ("drawer-open", (10.6, 1.9, 4.4), (10.6, 1.5, 0.8)),
        ("case-file", (9.52, 1.7, 2.95), (9.52, 1.30, 1.78)),
    )
    frame = 0

    def hidden_mode(size, flags=0, **kwargs):
        return original_mode(size, flags | pygame.HIDDEN, **kwargs)

    def render(renderer, window_size, *args, **kwargs):
        nonlocal frame
        name, position, target = views[min(frame, len(views) - 1)]
        if frame == 1:
            drawer = next(o for o in renderer._level.objects if o.name == ARCHIVE_DRAWER_ID)
            drawer.set_state("open")
            drawer.update(1)
            StoryPropSystem(renderer._level).update(0)
        renderer._camera = Camera(position, target, 65, 0.1, 150)
        kwargs.update(hud_text="", aim_text="", debug_text="", dialog=None)
        original_render(renderer, window_size, *args, **kwargs)
        raw = renderer.context.screen.read(components=3, alignment=1)
        surface = pygame.image.fromstring(raw, window_size, "RGB")
        path = output / f"{name}.png"
        pygame.image.save(pygame.transform.flip(surface, False, True), path)
        print(path.resolve(), flush=True)
        frame += 1
        if frame >= len(views):
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    with patch.object(settings, "AUDIO_ENABLED", False), \
            patch("pygame.display.set_mode", side_effect=hidden_mode), patch.object(Renderer, "render", render):
        run_session(level_name="start")


if __name__ == "__main__":
    capture()
