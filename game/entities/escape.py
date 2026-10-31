from dataclasses import dataclass
import math

from engine.scene.entity import Entity


@dataclass
class EscapeGoal(Entity):
    """Невидимая область выхода с требованиями к инвентарю."""

    radius: float = 1.0
    required_keys: tuple[str, ...] = ()
    next_level: str | None = None

    def __post_init__(self):
        if not math.isfinite(self.radius) or self.radius <= 0:
            raise ValueError("Escape radius must be positive and finite")
        if any(not isinstance(key, str) or not key.strip() for key in self.required_keys):
            raise ValueError("Escape key IDs must not be empty")
        if self.next_level is not None and (
            not isinstance(self.next_level, str) or not self.next_level.strip()
        ):
            raise ValueError("Next level must be a nonempty level name")

    def reached(self, position, inventory) -> bool:
        return (math.dist(tuple(position), self.transform.position) <= self.radius
                and all(inventory.has_key(key) for key in self.required_keys))
