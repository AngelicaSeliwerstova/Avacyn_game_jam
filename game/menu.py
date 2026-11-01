"""Start/pause menus and small persistent player preferences."""
import json
from pathlib import Path
import pygame
from config import settings
from engine.scene.session import Dialog, DialogButton


class GameMenu:
    def __init__(self, path: Path, *, start_screen=True, on_camera_mode_changed=None):
        self.path = Path(path)
        self.fullscreen = False
        self.audio_enabled = settings.AUDIO_ENABLED
        self.camera_mode = "cameras"
        self._on_camera_mode_changed = on_camera_mode_changed
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                if type(data.get("fullscreen")) is bool:
                    self.fullscreen = data["fullscreen"]
                if type(data.get("audio_enabled")) is bool:
                    self.audio_enabled = data["audio_enabled"]
                if data.get("camera_mode") in ("cameras", "third_person"):
                    self.camera_mode = data["camera_mode"]
        except (OSError, ValueError, UnicodeError):
            pass
        self.page = "main" if start_screen else None
        self._return_page = "main"
        self._selected = 0
        self._message = ""

    def apply(self, window):
        settings.AUDIO_ENABLED = self.audio_enabled
        if window.fullscreen != self.fullscreen:
            try:
                window.toggle_fullscreen()
            except pygame.error:
                self.fullscreen = window.fullscreen
                self._message = "Не удалось изменить режим экрана."

    def _save(self):
        temporary = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps({"fullscreen": self.fullscreen,
                "audio_enabled": self.audio_enabled, "camera_mode": self.camera_mode}, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.path)
        except OSError:
            self._message = "Настройки применены, но сохранить файл не удалось."

    def remember_window(self, window):
        self.fullscreen = window.fullscreen
        self._message = ""
        self._save()

    def open_pause(self):
        self.page, self._selected, self._message = "pause", 0, ""

    def _buttons(self):
        if self.page == "mode":
            return (("От третьего лица", "menu_third_person"),
                    ("Камеры · Геймджем", "menu_cameras"), ("Назад", "menu_main"))
        if self.page == "settings":
            return (("Полный экран: " + ("вкл." if self.fullscreen else "выкл."), "menu_fullscreen"),
                    ("Звук: " + ("вкл." if self.audio_enabled else "выкл."), "menu_audio"),
                    ("Вид: " + ("третье лицо" if self.camera_mode == "third_person" else "камеры · Геймджем"), "menu_camera_mode"),
                    ("Назад", "menu_back"))
        return (("Начать" if self.page == "main" else "Продолжить", "menu_begin"),
                ("Настройки", "menu_settings"), ("Выход", "menu_quit"))

    @property
    def dialog(self):
        if self.page is None:
            return None
        buttons = tuple(DialogButton(label, action,
            (("return", "keypad enter") if i == self._selected else ())
            + (("escape",) if (action in ("menu_back", "menu_main") or self.page == "pause" and action == "menu_begin") else ()))
            for i, (label, action) in enumerate(self._buttons()))
        title = {"main": "АВАЦИН", "mode": "РЕЖИМ ИГРЫ", "pause": "ПАУЗА", "settings": "НАСТРОЙКИ"}[self.page]
        descriptions = ("Камера следует за героиней.\nWASD — движение, мышь — обзор.",
                        "Камеры наблюдения. Версия для геймджема.\nW/S — шаг, A/D — поворот.", "Вернуться в главное меню.")
        message = self._message or (descriptions[self._selected] if self.page == "mode" else
                                    "Alt + Enter — полный экран" if self.page == "settings" else "")
        return Dialog(title, message, buttons, presentation="menu")

    def _set_camera_mode(self, mode):
        self.camera_mode = mode
        if self._on_camera_mode_changed is not None:
            self._on_camera_mode_changed(mode)
        self._save()

    def navigate(self, delta):
        self._selected = (self._selected + delta) % len(self._buttons())

    def handle_action(self, action, window):
        if self.page is None or action not in {a for _, a in self._buttons()}:
            return False
        self._message = ""
        if action == "menu_quit":
            return "quit"
        if action == "menu_begin":
            if self.page == "main":
                self.page = "mode"
                self._selected = 0 if self.camera_mode == "third_person" else 1
            else:
                self.page = None
        elif action in ("menu_third_person", "menu_cameras"):
            self._set_camera_mode("third_person" if action == "menu_third_person" else "cameras")
            self.page = None
        elif action == "menu_main":
            self.page, self._selected = "main", 0
        elif action == "menu_settings":
            self._return_page, self.page, self._selected = self.page, "settings", 0
        elif action == "menu_back":
            self.page, self._selected = self._return_page, 1
        elif action == "menu_fullscreen":
            try:
                window.toggle_fullscreen()
            except pygame.error:
                self._message = "Не удалось изменить режим экрана."
            else:
                self.remember_window(window)
        elif action == "menu_audio":
            self.audio_enabled = not self.audio_enabled
            settings.AUDIO_ENABLED = self.audio_enabled
            self._save()
        elif action == "menu_camera_mode":
            self._set_camera_mode("third_person" if self.camera_mode == "cameras" else "cameras")
        return True
