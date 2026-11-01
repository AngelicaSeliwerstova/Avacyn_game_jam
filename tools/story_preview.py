"""Capture Act 0 UI over the real renderer without opening a visible window."""

from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from engine.rendering.renderer import Renderer
from game.campaign import Campaign
from main import run_session


def capture(output_dir="artifacts/story-qa"):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    session = Campaign().load_level("peaceful").session
    dialogs = [("title", session.dialog)]
    session.tick_presentation(4)
    session.actors["doctor"].request_talk()
    session.update(0)
    session.tick_presentation(0.20)
    dialogs.append(("typing", session.dialog))
    session.reveal_dialogue()
    dialogs.append(("spoken-line", session.dialog))
    while not any(button.action.startswith("story_choice:") for button in session.dialog.buttons):
        session.handle_action("story_next")
    dialogs.append(("choice", session.dialog))
    for floor in range(3):
        session.open_document("hospital_plan", floor)
        dialogs.append((f"plan-{floor + 1}", session.dialog))
    for page in range(3):
        session.open_document("mother_letter", page)
        dialogs.append((f"letter-{page + 1}", session.dialog))
    original_mode, original_render = pygame.display.set_mode, Renderer.render
    frame = 0

    def hidden_mode(size, flags=0, **kwargs):
        return original_mode(size, flags | pygame.HIDDEN, **kwargs)

    def render(renderer, window_size, *args, **kwargs):
        nonlocal frame
        name, dialog = dialogs[min(frame, len(dialogs) - 1)]
        kwargs["dialog"] = dialog
        original_render(renderer, window_size, *args, **kwargs)
        raw = renderer.context.screen.read(components=3, alignment=1)
        surface = pygame.image.fromstring(raw, window_size, "RGB")
        path = output / f"{name}.png"
        pygame.image.save(pygame.transform.flip(surface, False, True), path)
        print(path.resolve(), flush=True)
        frame += 1
        if frame >= len(dialogs):
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    with patch("pygame.display.set_mode", side_effect=hidden_mode), patch.object(Renderer, "render", render):
        run_session(level_name="start")


if __name__ == "__main__":
    capture()
