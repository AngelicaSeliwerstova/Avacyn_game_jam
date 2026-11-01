"""Exercise and capture the live start menu without changing player preferences."""
from pathlib import Path
import tempfile
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from engine.rendering.renderer import Renderer
from engine.core.application import Application
from game.menu import GameMenu
from main import run_session


def capture(mode='third_person'):
    output=Path('artifacts/menu-qa')
    output.mkdir(parents=True,exist_ok=True)
    folder=tempfile.TemporaryDirectory()
    menu=GameMenu(Path(folder.name)/'preferences.json')
    menu.fullscreen=False
    menu.audio_enabled=False
    original_render,original_mode=Renderer.render,pygame.display.set_mode
    original_run=Application.run
    app=None
    frame=0
    def run(instance):
        nonlocal app
        app=instance
        return original_run(instance)
    def make_menu(*args,**kwargs):
        menu._on_camera_mode_changed=kwargs['on_camera_mode_changed']
        return menu
    def render(renderer,size,*args,**kwargs):
        nonlocal frame
        original_render(renderer,size,*args,**kwargs)
        name=('start','settings','start-again','modes','opening','gameplay')[min(frame,5)]
        surface=pygame.image.fromstring(renderer.context.screen.read(components=3,alignment=1),size,'RGB')
        path=output/(mode+'-'+name+'.png')
        pygame.image.save(pygame.transform.flip(surface,False,True),path)
        print(path.resolve(),flush=True)
        if frame==0:
            for key in (pygame.K_DOWN,pygame.K_RETURN): pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=key))
        elif frame==1:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
        elif frame==2:
            for key in (pygame.K_UP,pygame.K_RETURN): pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=key))
        elif frame==3:
            keys=(pygame.K_UP,pygame.K_RETURN) if mode=='third_person' else (pygame.K_RETURN,)
            for key in keys: pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=key))
        elif frame==4:
            app._session.tick_presentation(4)
            for _ in range(20):
                if app._session.dialog is None: break
                app._session.reveal_dialogue()
                app._session.handle_action('story_next')
        else:
            assert app._controlled_entity.camera_mode==mode
            assert app._controlled_entity.fixed_camera_effect_active==(mode=='cameras')
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        frame+=1
    def hidden(size,flags=0,**kwargs): return original_mode(size,flags|pygame.HIDDEN,**kwargs)
    with patch('game.menu.GameMenu',side_effect=make_menu),patch('pygame.display.set_mode',side_effect=hidden),patch.object(Renderer,'render',render),patch.object(Application,'run',run):
        run_session(show_menu=True)
    folder.cleanup()

if __name__=='__main__':
    capture('third_person')
    capture('cameras')
