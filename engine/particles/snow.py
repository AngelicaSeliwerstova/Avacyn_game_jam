from dataclasses import dataclass
from math import isfinite
from random import Random

from engine.collision.aabb import AABB


@dataclass(frozen=True)
class SnowSettings:
    count: int
    height: float
    fall_speed: float
    flake_size: float
    color: tuple[int, int, int]
    seed: int

    def __post_init__(self):
        if not isinstance(self.count, int) or self.count < 0:
            raise ValueError("Snow count must be a nonnegative integer")
        if any(not isfinite(value) or value <= 0 for value in (
            self.height, self.fall_speed, self.flake_size,
        )):
            raise ValueError("Snow height, speed and size must be finite and positive")
        if len(self.color) != 3 or any(not 0 <= c <= 255 for c in self.color):
            raise ValueError("Snow needs an RGB color with channels from 0 to 255")


class Snowfall:
    """Постоянное поле снега: мировые XZ, падение в секундах, возврат наверх."""

    def __init__(self, settings: SnowSettings, bounds: AABB, obstacles: tuple[AABB, ...]):
        self.settings = settings
        self._elapsed = 0.0
        self._flakes = []
        random = Random(settings.seed)
        radius = settings.flake_size / 2
        if bounds.max_x - bounds.min_x <= 2 * radius or bounds.max_z - bounds.min_z <= 2 * radius:
            raise ValueError("Snow area must be larger than a flake")

        # Ограничение попыток позволяет обнаружить полностью закрытую карту.
        for _ in range(settings.count * 200):
            if len(self._flakes) == settings.count:
                break
            x = random.uniform(bounds.min_x + radius, bounds.max_x - radius)
            z = random.uniform(bounds.min_z + radius, bounds.max_z - radius)
            if any(box.intersects_circle(x, z, radius) for box in obstacles):
                continue
            self._flakes.append((
                x, random.uniform(0, settings.height), z,
                settings.fall_speed * random.uniform(0.8, 1.2),
            ))
        if len(self._flakes) != settings.count:
            raise ValueError("Not enough open space to place snow; reduce count or flake size")

    def update(self, delta_time: float):
        if not isfinite(delta_time) or delta_time < 0:
            raise ValueError("Snow delta time must be finite and nonnegative")
        self._elapsed += delta_time

    @property
    def positions(self) -> tuple[tuple[float, float, float], ...]:
        # Исходная высота сохраняется: результат не зависит от числа кадров.
        return tuple(
            (x, (height - speed * self._elapsed) % self.settings.height, z)
            for x, height, z, speed in self._flakes
        )
