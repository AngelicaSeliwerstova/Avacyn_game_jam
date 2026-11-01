import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import pygame
from config import controls, settings
from engine.core.application import Application
from engine.rendering.dialog import DialogOverlay, dialog_action_at, dialog_button_rects
from engine.scene.session import Dialog, Session
from game.menu import GameMenu
from game.ui import create_hud_style


class MenuTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'settings.json'
        mute = patch.object(settings, 'AUDIO_ENABLED', True)
        mute.start()
        self.addCleanup(mute.stop)
        self.window = SimpleNamespace(fullscreen=False, size=(1536, 864), handle_event=Mock())
        self.window.toggle_fullscreen = Mock(side_effect=self.toggle)
        self.menu = GameMenu(self.path)
        self.device = Mock()

    def toggle(self):
        self.window.fullscreen = not self.window.fullscreen

    def app(self, session=None):
        return Application((640,480),(640,480),'test',60,(0,0,0),(3,3),False,
                           SimpleNamespace(creator_mode=False),controls.INPUT_BINDINGS,Mock(),
                           session=session or Session(),menu=self.menu)

    def send(self, app, *events):
        with patch('pygame.event.get', return_value=events):
            app._handle_events(self.device, self.window)

    def key(self, key, **kwargs):
        return pygame.event.Event(pygame.KEYDOWN,key=key,**kwargs)

    def test_menu_holds_story_dialog_until_begin_and_pause_resumes_itself(self):
        story = Dialog('АКТ 1','Под софитами',(),presentation='title')
        app = self.app(Session(dialog=story))
        self.assertTrue(app._simulation_paused)
        self.assertEqual(app._active_dialog.presentation,'menu')
        self.send(app,self.key(pygame.K_RETURN))
        self.assertEqual(self.menu.page,'mode')
        self.assertIs(app._session.dialog,story)
        self.send(app,self.key(pygame.K_RETURN))
        self.assertIsNone(self.menu.dialog)
        self.assertIs(app._active_dialog,story)
        self.assertTrue(app._simulation_paused)
        app._session.dialog = None
        self.send(app,self.key(pygame.K_ESCAPE))
        self.assertEqual(self.menu.page,'pause')
        self.send(app,self.key(pygame.K_ESCAPE))
        self.assertFalse(app._simulation_paused)
        self.device.end_modal.assert_called_once()

    def test_keyboard_settings_fullscreen_and_audio_persist_without_starting_game(self):
        app=self.app()
        self.send(app,self.key(pygame.K_DOWN),self.key(pygame.K_RETURN))
        self.assertEqual(self.menu.page,'settings')
        self.send(app,self.key(pygame.K_RETURN))
        self.assertTrue(self.window.fullscreen)
        self.send(app,self.key(pygame.K_DOWN),self.key(pygame.K_RETURN))
        self.assertFalse(settings.AUDIO_ENABLED)
        restored=GameMenu(self.path)
        self.assertTrue(restored.fullscreen)
        self.assertFalse(restored.audio_enabled)
        self.assertEqual(json.loads(self.path.read_text()),{'fullscreen':True,'audio_enabled':False,'camera_mode':'cameras'})
        self.assertTrue(app._simulation_paused)
        self.send(app,self.key(pygame.K_ESCAPE))
        self.assertEqual(self.menu.page,'main')

    def test_alt_enter_never_confirms_start_or_a_story_line_and_ignores_repeat(self):
        app=self.app(Session(dialog=Dialog('Story','Unchanged',())))
        shortcut=self.key(pygame.K_RETURN,mod=pygame.KMOD_ALT)
        self.send(app,shortcut)
        self.assertTrue(self.window.fullscreen)
        self.assertEqual(self.menu.page,'main')
        self.send(app,self.key(pygame.K_RETURN,mod=pygame.KMOD_ALT,repeat=True))
        self.assertTrue(self.window.fullscreen)
        self.menu.page=None
        self.send(app,shortcut)
        self.assertFalse(self.window.fullscreen)
        self.assertEqual(app._session.dialog.message,'Unchanged')

    def test_mouse_hits_same_menu_buttons_in_a_letterboxed_window(self):
        pygame.font.init()
        overlay=DialogOverlay.__new__(DialogOverlay)
        overlay._style=create_hud_style()
        overlay._font=pygame.font.Font(str(overlay._style.font_path),18)
        overlay._title_font=pygame.font.Font(str(overlay._style.font_path),28)
        for page in ('main','mode','settings','pause'):
            self.menu.page=page
            dialog=self.menu.dialog
            surface=pygame.Surface((640,480),pygame.SRCALPHA)
            overlay._draw_menu(surface,dialog,(640,480),None)
            for button,rect in zip(dialog.buttons,dialog_button_rects(dialog,(640,480))):
                self.assertTrue(surface.get_rect().contains(rect))
                point=(192+rect.centerx*1.8,rect.centery*1.8)
                self.assertEqual(dialog_action_at(dialog,point,(1536,864),(640,480)),button.action)
        self.menu.page='main'
        app=self.app()
        rect=dialog_button_rects(self.menu.dialog,(640,480))[1]
        self.send(app,pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,
            pos=(192+rect.centerx*1.8,rect.centery*1.8)))
        self.assertEqual(self.menu.page,'settings')

    def test_mode_choice_applies_saves_and_returns_from_selection_without_starting(self):
        callback=Mock()
        self.menu._on_camera_mode_changed=callback
        app=self.app()
        self.assertEqual(self.menu.dialog.title,'АВАЦИН')
        self.send(app,self.key(pygame.K_RETURN),self.key(pygame.K_ESCAPE))
        self.assertEqual(self.menu.page,'main')
        callback.assert_not_called()
        self.send(app,self.key(pygame.K_RETURN),self.key(pygame.K_UP),self.key(pygame.K_RETURN))
        callback.assert_called_once_with('third_person')
        self.assertIsNone(self.menu.dialog)
        self.assertEqual(GameMenu(self.path).camera_mode,'third_person')
        self.menu.open_pause()
        self.menu.handle_action('menu_settings',self.window)
        self.menu.handle_action('menu_camera_mode',self.window)
        callback.assert_called_with('cameras')
        self.assertEqual(GameMenu(self.path).camera_mode,'cameras')
        self.menu.navigate(3)
        self.assertIn('return',self.menu.dialog.buttons[-1].keys)
        self.menu.handle_action('menu_back',self.window)
        self.assertEqual(self.menu.page,'pause')

    def test_corrupt_preferences_fall_back_and_startup_applies_saved_fullscreen(self):
        for text in ('bad json','[]','{"fullscreen":"false","audio_enabled":0}'):
            self.path.write_text(text)
            menu=GameMenu(self.path)
            self.assertFalse(menu.fullscreen)
            self.assertTrue(menu.audio_enabled)
        self.path.write_text('{"fullscreen":true,"audio_enabled":false}')
        menu=GameMenu(self.path)
        menu.apply(self.window)
        self.assertTrue(self.window.fullscreen)
        self.assertFalse(settings.AUDIO_ENABLED)
        self.window.toggle_fullscreen.assert_called_once()

    def test_window_failure_does_not_persist_a_false_success(self):
        self.menu.page='settings'
        self.window.toggle_fullscreen.side_effect=pygame.error('unsupported')
        self.menu.handle_action('menu_fullscreen',self.window)
        self.assertFalse(self.menu.fullscreen)
        self.assertFalse(self.path.exists())
        self.assertIn('Не удалось',self.menu.dialog.message)

if __name__=='__main__': unittest.main()
