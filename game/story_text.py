"""Paginate authored text using the same font and wrapping as the game UI."""

import pygame

from config import settings
from engine.rendering.hud import wrap_line
from game.ui import create_hud_style


def text_pages(text, presentation):
    pygame.font.init()
    style = create_hud_style()
    font = pygame.font.Font(str(style.font_path), style.font_size)
    width = settings.RENDER_SIZE[0] - (60 if presentation == "conversation" else 104)
    line_count = 3 if presentation == "conversation" else max(1, (settings.RENDER_SIZE[1] - 172) // font.get_linesize())
    lines = [line for paragraph in text.split("\n") for line in wrap_line(paragraph, width, font)]
    return ["\n".join(lines[start:start + line_count]) for start in range(0, len(lines), line_count)]
