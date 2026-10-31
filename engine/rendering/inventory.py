import pygame

from engine.rendering.hud import TextOverlay
from engine.scene.inventory import InventoryView, ITEMS_PER_PAGE


class InventoryOverlay(TextOverlay):
    """Сетка предметов поверх затемнённой сцены; страницы не ограничивают вместимость."""

    def __init__(self, context, style):
        super().__init__(context, style)
        self._inventory_key = None

    def surface(self, view: InventoryView, size):
        width, height = size
        scale = min(width / 640, height / 480)
        padding, gap = max(8, int(18 * scale)), max(4, int(10 * scale))
        font_path = str(self._style.font_path) if self._style.font_path else None
        font = pygame.font.Font(font_path, max(10, int(16 * scale)))
        heading = pygame.font.Font(font_path, max(16, int(26 * scale)))
        small = pygame.font.Font(font_path, max(9, int(13 * scale)))
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill((0, 0, 0, 175))
        panel = pygame.Rect(0, 0, min(width - 24, int(560 * scale)), min(height - 20, int(360 * scale)))
        panel.center = (width // 2, height // 2)
        pygame.draw.rect(surface, (20, 25, 25, 248), panel, border_radius=3)
        pygame.draw.rect(surface, (100, 110, 100), panel, 1, border_radius=3)
        light, muted = (224, 221, 204), (151, 164, 151)
        surface.blit(heading.render("ИНВЕНТАРЬ", True, light), (panel.x + padding, panel.y + padding))
        count = small.render(f"Предметов: {len(view.items)}", True, muted)
        surface.blit(count, (panel.right - padding - count.get_width(), panel.y + padding + 5))
        top = panel.y + max(40, int(65 * scale))
        bottom = panel.bottom - max(32, int(48 * scale))
        card_width = (panel.width - 2 * padding - 2 * gap) // 3
        card_height = (bottom - top - gap) // 2
        page = max(0, min(view.page, view.page_count - 1))
        items = view.items[page * ITEMS_PER_PAGE:(page + 1) * ITEMS_PER_PAGE]
        for index in range(ITEMS_PER_PAGE):
            card = pygame.Rect(panel.x + padding + (index % 3) * (card_width + gap),
                               top + (index // 3) * (card_height + gap), card_width, card_height)
            pygame.draw.rect(surface, (29, 36, 34), card)
            pygame.draw.rect(surface, (65, 77, 68), card, 1)
            if index >= len(items):
                continue
            item = items[index]
            icon = max(12, int(25 * scale))
            cx, cy = card.centerx, card.y + gap + icon // 2
            ink = (187, 165, 109) if item.kind == "key" else (151, 171, 152)
            if item.kind == "key":
                pygame.draw.circle(surface, ink, (cx - icon // 3, cy), max(3, icon // 4), 2)
                pygame.draw.line(surface, ink, (cx - icon // 10, cy), (cx + icon // 2, cy), 2)
                pygame.draw.line(surface, ink, (cx + icon // 2, cy), (cx + icon // 2, cy + icon // 4), 2)
            else:
                pygame.draw.rect(surface, ink, (cx - icon // 2, cy - icon // 2, icon, icon), 2)
                pygame.draw.line(surface, ink, (cx, cy - icon // 2), (cx, cy + icon // 2), 1)
            lines = self._wrap_line(item.name, card.width - 10, font)
            available = max(1, (card.height - gap - icon - 5) // font.get_linesize())
            for line_index, line in enumerate(lines[:available]):
                if line_index == available - 1 and len(lines) > available:
                    while line and font.size(line + "…")[0] > card.width - 10:
                        line = line[:-1]
                    line += "…"
                text = font.render(line, True, light)
                surface.blit(text, (card.centerx - text.get_width() // 2,
                                   card.y + gap + icon + 5 + line_index * font.get_linesize()))
            if item.quantity > 1:
                text = small.render(f"×{item.quantity}", True, muted)
                surface.blit(text, (card.right - text.get_width() - 5, card.y + 4))
        if not view.items:
            lines = self._wrap_line("Пока пусто — найденные предметы появятся здесь", panel.width - 2 * padding, font)
            for i, line in enumerate(lines):
                text = font.render(line, True, light)
                rect = text.get_rect(center=(panel.centerx, (top + bottom) // 2 + i * font.get_linesize()))
                pygame.draw.rect(surface, (20, 25, 25), rect.inflate(12, 8))
                surface.blit(text, rect)
        hint = small.render(f"{view.close_key} / Esc — закрыть", True, muted)
        surface.blit(hint, (panel.x + padding, panel.bottom - padding - hint.get_height()))
        if view.page_count > 1:
            text = small.render(f"← →  {page + 1} / {view.page_count}", True, muted)
            surface.blit(text, (panel.right - padding - text.get_width(), panel.bottom - padding - text.get_height()))
        return surface

    def draw(self, view: InventoryView, render_size):
        key = (view, render_size)
        if key != self._inventory_key:
            self._upload_surface(self.surface(view, render_size))
            self._inventory_key = key
        self._draw_texture(render_size, "center")
