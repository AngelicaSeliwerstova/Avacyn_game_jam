"""Bake crisp Cyrillic room numbers into world-space plaque textures."""

from pathlib import Path
import sys

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from game.levels.room_signs import PATIENT_SIGNS


def generate():
    pygame.font.init()
    output = ROOT / "resources/textures/signs"
    output.mkdir(parents=True, exist_ok=True)
    font_path = ROOT / "resources/fonts/SourceSans3-Semibold.ttf"
    for size in (128, 256):
        font = pygame.font.Font(str(font_path), round(size * 0.48))
        for name, text in PATIENT_SIGNS.items():
            surface = pygame.Surface((size * 4, size))
            surface.fill((25, 45, 43))
            pygame.draw.rect(surface, (177, 187, 160), surface.get_rect().inflate(-12, -12), 2)
            lines = text.splitlines()
            if len(lines) > 1:
                face = pygame.font.Font(str(font_path), round(size * 0.35))
            else:
                face = font
            line_height = face.get_linesize()
            top = (size - len(lines) * line_height) // 2
            for index, line in enumerate(lines):
                label = face.render(line, True, (238, 238, 206))
                surface.blit(label, label.get_rect(center=(size * 2, top + index * line_height + line_height // 2)))
            pygame.image.save(surface, str(output / f"{name}_{size}.png"))


if __name__ == "__main__":
    generate()
