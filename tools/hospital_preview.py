"""Render repeatable interior QA views using the real game renderer."""

import argparse
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from engine.rendering.renderer import Renderer
from engine.scene.camera import Camera
from main import run_session


VIEWS = {
    "ground_ward": ((11.5, 2.2, -8.5), (11, 1.0, -12.4)),
    "ground_office": ((-16, 2.0, -8.5), (-18.0, 1.0, -13)),
    "surgery_storage": ((23, 7.0, -12.5), (24, 6.0, -21)),
    "patient_room": ((-23, 11.8, -14), (-26.2, 10.4, -20.5)),
    "patient_ceiling": ((-24, 11.3, -14), (-24, 14.15, -20)),
    "second_landing": ((-8, 6.4, 7.3), (-13, 5.5, 5.8)),
    "upper_flight": ((-16.1, 9.0, 4), (-13, 9.4, 6.8)),
    "roof": ((5, 26, 25), (-2, 12, -3)),
}


def capture_views(level_name, output_dir, view_names):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    set_mode, render = pygame.display.set_mode, Renderer.render
    frames = 0

    def hidden_mode(size, flags=0, **kwargs):
        return set_mode(size, flags | pygame.HIDDEN, **kwargs)

    def capture(renderer, window_size, *args, **kwargs):
        nonlocal frames
        name = view_names[min(frames, len(view_names) - 1)]
        position, target = VIEWS[name]
        renderer._camera = Camera(position, target, 65, 0.1, 150)
        kwargs.update(hud_text="", aim_text="", debug_text="")
        render(renderer, window_size, *args, **kwargs)
        raw = renderer.context.screen.read(components=3, alignment=1)
        surface = pygame.image.fromstring(raw, window_size, "RGB")
        path = output / f"{level_name}_{name}.png"
        pygame.image.save(pygame.transform.flip(surface, False, True), path)
        print(path.resolve(), flush=True)
        frames += 1
        if frames >= len(view_names):
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    with patch("pygame.display.set_mode", side_effect=hidden_mode), patch.object(Renderer, "render", capture):
        run_session(level_name=level_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", default="start", choices=("start", "peaceful"))
    parser.add_argument("--output-dir", default="artifacts/interior-qa")
    parser.add_argument("--views", nargs="+", choices=tuple(VIEWS), default=tuple(VIEWS))
    args = parser.parse_args()
    capture_views(args.level, args.output_dir, args.views)
