"""Capture the revised campaign's final staging without opening a window."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import glm
import moderngl
import pygame
from config import settings
from engine.input.state import InputState
from engine.rendering.renderer import Renderer
from engine.rendering.cctv_overlay import CCTVOverlay
from engine.scene.camera import Camera
from game.campaign import Campaign
from game.materials import create_texture_settings
from game.ui import create_hud_style


def advance(session):
    for _ in range(2000):
        if session.next_level or session.puzzle_active:
            return
        if session.dialog:
            if session.dialog.presentation == 'ending':
                return
            if session.dialog.buttons:
                session.reveal_dialogue()
                session.handle_action(session.dialog.buttons[0].action)
                continue
        elif not session.controls_locked:
            return
        session.tick_presentation(.25)
        for obj in session.level.objects:
            obj.update(.25)
        session.update(.25)


def capture():
    settings.AUDIO_ENABLED = False
    pygame.font.init()
    output = Path('artifacts/campaign-qa')
    output.mkdir(parents=True, exist_ok=True)
    size = (960, 720)
    context = moderngl.create_standalone_context(require=330)
    screen = context.simple_framebuffer(size)
    context._screen = screen
    campaign = Campaign()
    scene = campaign.load_level('act2')
    advance(scene.session)

    def renderer_for(scene):
        return Renderer(size, settings.BACKGROUND_COLOR, settings.OPENGL_VERSION, scene.player.camera,
                        scene.level, textures=create_texture_settings(), hud_style=create_hud_style(),
                        postprocess=scene.postprocess, fog=scene.fog, player_model=scene.player.model, context=context)

    def save(renderer, name, **kw):
        renderer.update(0)
        renderer.render(size, **kw)
        image = pygame.image.frombytes(screen.read(components=3, alignment=1), size, 'RGB')
        pygame.image.save(pygame.transform.flip(image, False, True), str(output / f'{name}.png'))
        print(output / f'{name}.png', flush=True)

    renderer = renderer_for(scene)
    renderer._camera = Camera((-8.8, 2.8, 11.8), (-12.1, .35, 9.65), 60, .1, 100)
    save(renderer, 'friend_and_pendant')
    scene.player.body._position = glm.vec3(-10, 0, 10)
    scene.session.update(0)
    advance(scene.session)
    scene.player.update(0, InputState())
    renderer._camera = scene.player.camera
    save(renderer, 'accept_help', aim_text=scene.player.aim_text)
    renderer.release(release_context=False)
    scene.session.release()

    scene = Campaign().load_level('healed')
    advance(scene.session)
    scene.player.body._position = glm.vec3(18.5, 9.6, 4.5)
    scene.player.controller._yaw = .15
    scene.player.controller._pitch = -.1
    scene.player._sync_third_person_camera()
    renderer = renderer_for(scene)
    save(renderer, 'ward_313')
    puzzle = scene.session._puzzles['cctv_archive']
    puzzle.progress.order = list('ABCD')
    puzzle.check()
    puzzle.play()
    puzzle._step = next(i for i, step in enumerate(puzzle.data['recording']) if len(step.get('text', '')) > 250)
    puzzle._begin_step()
    overlay = CCTVOverlay(context, create_hud_style())
    pygame.image.save(overlay.surface(puzzle.view(), (640, 480)), str(output / 'recording_subtitles.png'))
    overlay.release()
    renderer.release(release_context=False)
    scene.session.release()
    screen.release()
    context.release()


if __name__ == '__main__':
    capture()
