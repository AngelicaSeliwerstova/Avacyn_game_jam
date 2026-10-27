from engine.scene.session import Dialog, DialogButton, Session
from game.entities.escape import EscapeGoal


class GameSession(Session):
    def __init__(self, level=None, player=None):
        super().__init__()
        self.player = player
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
        if self.dialog is not None or self.player is None:
            return
        for goal in self.goals:
            if goal.reached(self.player.body.position, self.player.inventory):
                self.dialog = Dialog("Ты выбрался", "", self._buttons())
                return
        self._update_hint()

    def _update_hint(self):
        self.player.objective_status = ""
        if not self.goals:
            return
        for key in self.goals[0].required_keys:
            if not self.player.inventory.has_key(key):
                self.player.objective_status = f"Find: {self._key_names.get(key, key)}."
                return
        self.player.objective_status = "Unlock the balcony door and escape."
