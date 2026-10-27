from dataclasses import dataclass


@dataclass(frozen=True)
class Interaction:
    """Подпись, ответ и команда, которую обрабатывают правила игры."""

    name: str
    message: str
    action: str = "Inspect"
    command: str = "inspect"
    argument: str = ""

    def __post_init__(self):
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.name, self.message, self.action, self.command)):
            raise ValueError("Interaction name, message and action must be nonempty strings")
        if not isinstance(self.argument, str):
            raise ValueError("Interaction argument must be a string")
