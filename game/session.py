from dataclasses import replace

from engine.scene.session import Dialog, DialogButton, Session
from game.entities.escape import EscapeGoal
from game.entities.companion import Companion
from game.dialogue_voice import DialogueTyper, DialogueVoiceProfile


class GameSession(Session):
    def __init__(self, level=None, player=None, flags=None):
        super().__init__()
        self.player = player
        self._flags = flags if flags is not None else set()
        if level is not None:
            from game.levels.patient_archive import restore_patient_archive
            restore_patient_archive(level, self._flags)
        self.companions = tuple(obj.entity for obj in level.objects if isinstance(obj.entity, Companion)) if level else ()
        self._speaker = None
        self._dialogue_index = 0
        self._typing = None
        self._spoken_buttons = ()
        self.goals = tuple(obj.entity for obj in level.objects if isinstance(obj.entity, EscapeGoal)) if level else ()
        self._key_names = {obj.interaction.argument: obj.interaction.name for obj in level.objects
                           if obj.interaction is not None and obj.interaction.command == "pickup_key"} if level else {}
        if player is not None:
            self._update_hint()

    @staticmethod
    def _buttons():
        return (DialogButton("Заново   Enter", "restart", ("return", "keypad enter", "r")),
                DialogButton("Выйти   Esc", "quit", ("escape",)))

    def lose(self):
        if self.dialog is None:
            self.dialog = Dialog(
                "Ты проиграл", "", self._buttons(),
            )

    def update(self, delta_time):
        if self.dialog is not None or self.next_level is not None or self.player is None:
            return
        for ally in self.companions:
            if ally.talk_requested and ally.dialogue:
                ally.talk_requested = False
                self._speaker = ally
                self._dialogue_index = 0
                self._show_conversation()
                return
        for goal in self.goals:
            if goal.reached(self.player.body.position, self.player.inventory):
                if goal.next_level is not None:
                    self.next_level = goal.next_level
                else:
                    self.dialog = Dialog("Ты выбрался", "", self._buttons())
                return
        self._update_hint()

    def _update_hint(self):
        self.player.objective_status = ""
        if any(ally.dialogue and not ally.following for ally in self.companions):
            self.player.objective_status = "Поговорите с человеком в дальнем кабинете."
            return
        if not self.goals:
            return
        for key in self.goals[0].required_keys:
            if not self.player.inventory.has_key(key):
                self.player.objective_status = f"Find: {self._key_names.get(key, key)}."
                return
        self.player.objective_status = self.goals[0].hint or "Reach the exit."

    def _show_conversation(self):
        self.stop_dialogue_voice()
        node = self._speaker.dialogue[self._dialogue_index]
        if isinstance(node, dict):
            self.dialog = Dialog(self._speaker.display_name, node["text"], tuple(
                DialogButton(f"{index + 1}. {choice['label']}", f"dialogue_choice:{index}",
                             (str(index + 1), "escape") if choice.get("end") == "close" else (str(index + 1),))
                for index, choice in enumerate(node["choices"])
            ), presentation="conversation")
            return
        last = self._dialogue_index == len(self._speaker.dialogue) - 1
        self.show_spoken_line(self._speaker.display_name, self._speaker.dialogue[self._dialogue_index],
                             (DialogButton("Пойдём   E / Enter" if last else "Далее   E / Enter",
                                           "dialogue_next", ("e", "return", "keypad enter")),),
                             DialogueVoiceProfile())

    def show_spoken_line(self, speaker, text, buttons, voice, presentation="conversation"):
        self.stop_dialogue_voice()
        self._typing = DialogueTyper(text, voice)
        self._spoken_buttons = buttons
        typing_buttons = tuple(replace(button, label="Показать целиком   E / Enter") for button in buttons)
        self.dialog = Dialog(speaker, text, typing_buttons, presentation=presentation, visible_characters=0)

    def stop_dialogue_voice(self):
        self._typing = None

    def reveal_dialogue(self):
        """First continue press reveals the line; the next advances the story."""
        if self._typing is None or self.dialog is None:
            return False
        self._typing.reveal()
        self.dialog = replace(self.dialog, visible_characters=len(self.dialog.message), buttons=self._spoken_buttons)
        self.stop_dialogue_voice()
        return True

    def tick_presentation(self, delta_time):
        if self._typing is None or self.dialog is None:
            return
        self._typing.update(delta_time)
        self.dialog = replace(self.dialog, visible_characters=self._typing.visible,
                              buttons=self._spoken_buttons if self._typing.finished else self.dialog.buttons)
        if self._typing.finished:
            self._typing = None

    def release(self):
        self._typing = None

    def handle_action(self, action):
        if self._speaker is None or self.dialog is None:
            return False
        node = self._speaker.dialogue[self._dialogue_index]
        if isinstance(node, dict):
            if action not in {button.action for button in self.dialog.buttons}:
                return False
            choice = node["choices"][int(action.split(":")[1])]
            if "flag" in choice:
                self._flags.add(choice["flag"])
            if "next" in choice:
                self._dialogue_index = choice["next"]
                self._show_conversation()
            else:
                self._finish_conversation(choice["end"] == "recruit")
            return True
        if action != "dialogue_next":
            return False
        if self.reveal_dialogue():
            return True
        self._dialogue_index += 1
        if self._dialogue_index < len(self._speaker.dialogue):
            self._show_conversation()
        else:
            self._finish_conversation(True)
        return True

    def _finish_conversation(self, recruit):
        self.stop_dialogue_voice()
        if recruit:
            self._speaker.following = True
            self._flags.add(f"recruited:{self._speaker.name}")
            self.next_level = self._speaker.next_level
        self._speaker = None
        self.dialog = None
        self._update_hint()
