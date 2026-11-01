"""Render Act 1's office, five drawers and empty cradle with the real renderer."""
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from config import settings
from engine.rendering.renderer import Renderer
from engine.scene.camera import Camera
from game.campaign import Campaign
from game.levels.under_spotlights import MEMORY_CAMERA, CRADLE_TARGET
from main import run_session


def capture():
    output=Path('artifacts/spotlights-qa')
    output.mkdir(parents=True,exist_ok=True)
    session=Campaign().load_level('start').session
    session._files.show()
    years=session.dialog
    session.open_document('mother_letter')
    session._show_document(len(session._document_pages)-1)
    last_page=session.dialog
    session._advance()
    session._queue.clear()
    session._prepend(session.act,[{'type':'voiceover','id':'cradle_memory'}])
    session._advance()
    memory=session.dialog
    session.open_document('office_case')
    case=session.dialog
    groups=(('peaceful',(
        ('office-104',(-17,1.9,-7.8),(-19,1.15,-12),None),
        ('medical-case',(-17,1.9,-7.8),(-19,1.15,-12),case))),
        ('start',(
        ('archive-cabinet',(10.6,2.1,4.5),(10.6,1.45,.8),None),
        ('archive-years',(10.6,2.1,4.5),(10.6,1.45,.8),years),
        ('letter-final-page',(10.6,2.1,4.5),(10.6,1.45,.8),last_page),
        ('nursery-overview',(-16,6.7,-12),(-16,6.15,-21),None),
        ('empty-cradle',MEMORY_CAMERA,CRADLE_TARGET,None),
        ('memory-voices',MEMORY_CAMERA,CRADLE_TARGET,memory))))
    original_mode,original_render=pygame.display.set_mode,Renderer.render
    def hidden(size,flags=0,**kwargs): return original_mode(size,flags|pygame.HIDDEN,**kwargs)
    for level,views in groups:
        frame=0
        def render(renderer,window_size,*args,**kwargs):
            nonlocal frame
            name,position,target,dialog=views[min(frame,len(views)-1)]
            renderer._camera=Camera(position,target,65,.1,150)
            kwargs.update(dialog=dialog,aim_text='',hud_text='',debug_text='')
            original_render(renderer,window_size,*args,**kwargs)
            raw=renderer.context.screen.read(components=3,alignment=1)
            surface=pygame.image.fromstring(raw,window_size,'RGB')
            path=output/(name+'.png')
            pygame.image.save(pygame.transform.flip(surface,False,True),path)
            print(path.resolve(),flush=True)
            frame+=1
            if frame>=len(views): pygame.event.post(pygame.event.Event(pygame.QUIT))
        with patch.object(settings,'AUDIO_ENABLED',False),patch('pygame.display.set_mode',side_effect=hidden),patch.object(Renderer,'render',render):
            run_session(level_name=level)
    session.release()

if __name__=='__main__': capture()
