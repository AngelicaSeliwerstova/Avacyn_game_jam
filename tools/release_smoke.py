"""Exercise bundled GPU rendering and decode assets without a visible window."""
from pathlib import Path
import json


def verify():
    import moderngl
    import pygame
    from config import settings
    from engine.rendering.renderer import Renderer
    from game.campaign import Campaign
    from game.materials import create_texture_settings
    from game.ui import create_hud_style
    from game.menu import GameMenu
    from config.paths import data_directory

    settings.AUDIO_ENABLED = False
    pygame.display.init()
    pygame.font.init()
    # The dummy device still exercises SDL's audio decoders and bundled DLLs.
    import os
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.mixer.init()
    root = Path(settings.__file__).resolve().parents[1]
    audio = sorted((root / "resources/audio").rglob("*.wav"))
    for path in audio:
        pygame.mixer.Sound(str(path))
    context = moderngl.create_standalone_context(require=330)
    size = (640, 480)
    screen = context.simple_framebuffer(size)
    context._screen = screen
    levels = ("peaceful", "start", "act1", "act2", "healed")
    try:
        for name in levels:
            scene = Campaign().load_level(name)
            renderer = Renderer(size, settings.BACKGROUND_COLOR, settings.OPENGL_VERSION,
                scene.player.camera, scene.level, textures=create_texture_settings(),
                hud_style=create_hud_style(), postprocess=scene.postprocess, fog=scene.fog,
                player_model=scene.player.model, context=context)
            try:
                renderer.update(0)
                renderer.render(size)
                assert len(screen.read(components=3, alignment=1)) == size[0] * size[1] * 3
                menu = GameMenu(data_directory() / "saves/settings.json")
                renderer.render(size, dialog=menu.dialog)
                print(f"Rendered {name}", flush=True)
            finally:
                renderer.release(release_context=False)
                scene.session.release()
    finally:
        screen.release()
        context.release()
        pygame.quit()
    result = {"status": "passed", "levels": levels, "audio_files": len(audio)}
    (data_directory() / "smoke-test.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("Release smoke test passed", flush=True)
