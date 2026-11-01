"""Capture the editable Act 1 title, memory, TV flash and ending in the real renderer."""
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from engine.rendering.renderer import Renderer
from engine.scene.camera import Camera
from engine.scene.session import Dialog
from game.campaign import Campaign
from main import run_session


def capture(output_dir="artifacts/act1-qa"):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    scene = Campaign().load_level("act1")
    session = scene.session
    title = session.dialog
    session.tick_presentation(4)
    session.reveal_dialogue()
    intro = session.dialog
    session._queue.clear()
    session._dialogue_nodes(session.act, session.act.dialogues["memory"], "memory")
    session._advance()
    session.reveal_dialogue()
    memory = session.dialog
    end = next(step for item in session.act.data["scenes"] for step in item["steps"] if step["type"] == "end")
    ending = Dialog(end["title"], end["text"], session._buttons(), presentation="ending")
    child = ((28, 11.8, -18.1), (23.2, 11.2, -21.3))
    views = (("act1-title", title, None), ("act1-intro", intro, None),
             ("act1-memory", memory, child), ("act1-ending", ending, child),
             ("tv-flash", None, ((11, 11.25, -19.5), (11, 11.05, -22.5))))
    original_mode, original_render = pygame.display.set_mode, Renderer.render
    frame = 0

    def hidden_mode(size, flags=0, **kwargs):
        return original_mode(size, flags | pygame.HIDDEN, **kwargs)

    def render(renderer, window_size, *args, **kwargs):
        nonlocal frame
        name, dialog, camera = views[min(frame, len(views) - 1)]
        if camera is not None:
            renderer._camera = Camera(*camera, 65, 0.1, 150)
        if name == "tv-flash":
            next(o for o in renderer._level.objects if o.name == "f3_ward_306_tv").set_state("memory")
        kwargs.update(dialog=dialog, hud_text="", aim_text="", inventory=None)
        original_render(renderer, window_size, *args, **kwargs)
        raw = renderer.context.screen.read(components=3, alignment=1)
        image = pygame.image.fromstring(raw, window_size, "RGB")
        path = output / f"{name}.png"
        pygame.image.save(pygame.transform.flip(image, False, True), path)
        print(path.resolve(), flush=True)
        frame += 1
        if frame >= len(views):
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    with patch("pygame.display.set_mode", side_effect=hidden_mode), patch.object(Renderer, "render", render):
        run_session(level_name="act1")


if __name__ == "__main__":
    capture()
