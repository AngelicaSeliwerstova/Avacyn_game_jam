"""Bake dated drawer labels for the reception's personal-file cabinet."""

from pathlib import Path
import sys

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from game.levels.patient_archive import ARCHIVE_YEARS


def generate():
    pygame.font.init()
    output = ROOT / "resources/textures/signs"
    output.mkdir(parents=True, exist_ok=True)
    font_path = ROOT / "resources/fonts/SourceSans3-Semibold.ttf"
    for size in (128, 256):
        for year in ARCHIVE_YEARS:
            surface = pygame.Surface((size * 4, size))
            surface.fill((210, 198, 163))
            pygame.draw.rect(surface, (104, 85, 54), surface.get_rect().inflate(-8, -8), 4)
            font = pygame.font.Font(str(font_path), round(size * 0.94))
            text = font.render(str(year), True, (37, 44, 37))
            surface.blit(text, text.get_rect(center=surface.get_rect().center))
            pygame.image.save(surface, str(output / f"archive_year_{year}_{size}.png"))
        surface = pygame.Surface((size * 8, size))
        surface.fill((28, 43, 37))
        pygame.draw.rect(surface, (168, 166, 125), surface.get_rect().inflate(-8, -8), 3)
        font = pygame.font.Font(str(font_path), round(size * 0.72))
        title = "АРХИВ / 1975–1990"
        font_size = round(size * 0.72)
        while font.size(title)[0] > surface.get_width() - size // 2:
            font_size -= 2
            font = pygame.font.Font(str(font_path), font_size)
        text = font.render(title, True, (228, 218, 179))
        surface.blit(text, text.get_rect(center=surface.get_rect().center))
        pygame.image.save(surface, str(output / f"archive_heading_{size}.png"))
        office = pygame.Surface((size * 4, size))
        office.fill((28, 43, 37))
        font_size = round(size * 0.76)
        font = pygame.font.Font(str(font_path), font_size)
        while font.size("КАБИНЕТ 104")[0] > office.get_width() - size // 4:
            font_size -= 2
            font = pygame.font.Font(str(font_path), font_size)
        text = font.render("КАБИНЕТ 104", True, (228, 218, 179))
        office.blit(text, text.get_rect(center=office.get_rect().center))
        pygame.image.save(office, str(output / f"archive_office_104_{size}.png"))


if __name__ == "__main__":
    generate()
