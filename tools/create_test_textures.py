"""Создаёт две нейтральные бесшовные текстуры для проверки рендера."""

from math import cos, sin, tau
from pathlib import Path
from random import Random

import pygame


ROOT = Path(__file__).resolve().parents[1] / "resources" / "textures"
SIZE = 128


def main():
    for name, base, seed in (
        ("samples/concrete.png", (73, 76, 72), 13),
        ("samples/plaster.png", (120, 116, 105), 29),
    ):
        path = ROOT / name
        if path.exists():
            print(f"Keep existing: {path}")
            continue
        random = Random(seed)
        image = pygame.Surface((SIZE, SIZE))
        for y in range(SIZE):
            for x in range(SIZE):
                u, v = tau * x / SIZE, tau * y / SIZE
                value = (4 * sin(u + 0.7) * cos(v) + 2 * sin(3 * u + 2 * v)
                         + 1.5 * cos(5 * u - 4 * v) + random.uniform(-1.5, 1.5))
                image.set_at((x, y), tuple(round(channel + value) for channel in base))
        path.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(image, str(path))
        print(f"Created: {path}")


if __name__ == "__main__":
    main()
