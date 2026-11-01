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
    presentation: str = "modal"
    opacity: float = 1.0
    effect_time: float = 0.0
    plan_walls: tuple[tuple[float, float, float, float], ...] = ()
    plan_labels: tuple[tuple[float, float, str], ...] = ()
    plan_player: tuple[float, float] | None = None
    plan_stair: tuple[float, float, float] | None = None
    plan_highlights: tuple[str, ...] = ()
    visible_characters: int | None = None


@dataclass
class Session:
    """Открытый диалог приостанавливает симуляцию и получает ввод вместо игрока."""

    dialog: Dialog | None = None
    next_level: str | None = None
    controls_locked: bool = False
    puzzle_view: object | None = None

    @property
    def puzzle_active(self):
        return self.puzzle_view is not None

    def handle_puzzle_action(self, action: str) -> bool:
        return False

    def tick_presentation(self, delta_time: float):
        """Advance timed overlays even while a dialog pauses the simulation."""

    def handle_gameplay_key(self, key: str) -> bool:
        return False

    def handle_action(self, action: str) -> bool:
        """True when a game dialog consumes an action without exiting the app."""
        return False
