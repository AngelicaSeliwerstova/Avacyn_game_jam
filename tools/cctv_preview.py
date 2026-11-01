"""Render recorder UI states with real frame assets and the game renderer."""
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from engine.rendering.renderer import Renderer
from game.campaign import Campaign
from main import run_session


def capture():
    folder = Path("artifacts/cctv-qa")
    folder.mkdir(parents=True, exist_ok=True)
    scene = Campaign().load_level("act1")
    puzzle = scene.session._puzzles["cctv_archive"]
    views = [("initial", puzzle.view())]
    puzzle.click(0)
    views.append(("selected", puzzle.view()))
    puzzle.check()
    puzzle.check()
    puzzle.hint()
    views.append(("hint", puzzle.view()))
    puzzle.progress.order = list(puzzle.data["correct_order"])
    puzzle.check()
    views.append(("solved", puzzle.view()))
    puzzle.play()
    views.append(("playback-a", puzzle.view()))
    for _ in range(3000):
        puzzle.tick(0.1)
        view = puzzle.view()
        if view.speaker.startswith("Неизвестная") and view.caption:
            views.append(("unknown-line", view))
            break
        if puzzle.playing:
            puzzle.continue_recording()
    original_render, original_mode = Renderer.render, pygame.display.set_mode
    frame = 0

    def render(renderer, window_size, *args, **kwargs):
        nonlocal frame
        name, view = views[min(frame, len(views) - 1)]
        kwargs.update(dialog=None, puzzle_view=view, inventory=None, hud_text="", aim_text=None)
        original_render(renderer, window_size, *args, **kwargs)
        raw = renderer.context.screen.read(components=3, alignment=1)
        surface = pygame.image.fromstring(raw, window_size, "RGB")
        pygame.image.save(pygame.transform.flip(surface, False, True), folder / f"{name}.png")
        frame += 1
        if frame >= len(views):
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    with patch.object(Renderer, "render", render), patch("pygame.display.set_mode", side_effect=
            lambda size, flags=0, **kw: original_mode(size, flags | pygame.HIDDEN, **kw)):
        run_session(level_name="act1")
    scene.session.release()
    print(folder.resolve())


if __name__ == "__main__":
    capture()
