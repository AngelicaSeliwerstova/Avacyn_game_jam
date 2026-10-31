from engine.scene.session import Dialog, DialogButton, Session
from game.entities.escape import EscapeGoal
from game.entities.companion import Companion


class GameSession(Session):
    def __init__(self, level=None, player=None, flags=None):
        super().__init__()
        self.player = player
        self._flags = flags if flags is not None else set()
        self.companions = tuple(obj.entity for obj in level.objects if isinstance(obj.entity, Companion)) if level else ()
        self._speaker = None
        self._dialogue_index = 0
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
            if ally.talk_requested:
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
        last = self._dialogue_index == len(self._speaker.dialogue) - 1
        self.dialog = Dialog(self._speaker.display_name, self._speaker.dialogue[self._dialogue_index],
                             (DialogButton("Пойдём   E / Enter" if last else "Далее   E / Enter",
                                           "dialogue_next", ("e", "return", "keypad enter")),))

    def handle_action(self, action):
        if action != "dialogue_next" or self._speaker is None:
            return False
        self._dialogue_index += 1
        if self._dialogue_index < len(self._speaker.dialogue):
            self._show_conversation()
        else:
            self._speaker.following = True
            self._flags.add(f"recruited:{self._speaker.name}")
            self.next_level = self._speaker.next_level
            self._speaker = None
            self.dialog = None
            self._update_hint()
        return True
