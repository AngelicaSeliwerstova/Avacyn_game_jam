from dataclasses import dataclass


@dataclass(frozen=True)
class DialogButton:
    label: str
    action: str
    keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class Dialog:
    title: str
    message: str
    buttons: tuple[DialogButton, ...]


@dataclass
class Session:
    """Открытый диалог приостанавливает симуляцию и получает ввод вместо игрока."""

    dialog: Dialog | None = None
    next_level: str | None = None

    def handle_action(self, action: str) -> bool:
        """True when a game dialog consumes an action without exiting the app."""
        return False
