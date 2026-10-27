from engine.scene.session import Dialog, DialogButton, Session


class GameSession(Session):
    def lose(self):
        if self.dialog is None:
            self.dialog = Dialog(
                "YOU LOST", "The snail caught you.",
                (DialogButton("Try again [Enter]", "restart", ("return", "keypad enter", "r")),
                 DialogButton("Quit [Esc]", "quit", ("escape",))),
            )
