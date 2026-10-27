from dataclasses import dataclass


@dataclass(frozen=True)
class Interaction:
    """Подпись действия и ответ объекта при осмотре."""

    name: str
    message: str
    action: str = "Inspect"

    def __post_init__(self):
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.name, self.message, self.action)):
            raise ValueError("Interaction name, message and action must be nonempty strings")
