"""Export floor plans from actual collision geometry, including door swings.

Run: .venv/Scripts/python.exe tools/hospital_plans.py --output-dir artifacts/plans
"""

import argparse
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from game.levels import create_level


def export_plans(output_dir, level_name="start"):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pygame.font.init()
    font = pygame.font.SysFont("segoeui", 12)
    title_font = pygame.font.SysFont("segoeui", 24, bold=True)
    level = create_level(level_name)
    scale, margin = 17, 45

    def point(x, z):
        return (round((x + width / 2) * scale + margin),
                round((z + depth / 2) * scale + margin + 50))

    def polygon(surface, box, color):
        x, _, z = box.position
        hx, _, hz = (v / 2 for v in box.size)
        c, s = math.cos(math.radians(box.yaw_degrees)), math.sin(math.radians(box.yaw_degrees))
        corners = [point(x + c * dx + s * dz, z - s * dx + c * dz)
                   for dx, dz in ((-hx, -hz), (hx, -hz), (hx, hz), (-hx, hz))]
        pygame.draw.polygon(surface, color, corners)

    for floor, height in enumerate(level.floor_heights):
        width, depth = (43, 29) if floor == 0 else level.floor_size
        size = (round(width * scale + margin * 2), round(depth * scale + margin * 2 + 90))
        surface = pygame.Surface(size)
        surface.fill((237, 234, 223))
        surface.blit(title_font.render(level.floor_labels[floor], True, (30, 45, 47)), (margin, 15))
        legend = "Серые: стены и мебель. Двери: закрыта — оранжевая, открыта — зелёная; лифты — синие. Сетка: 2 м."
        surface.blit(font.render(legend, True, (55, 65, 65)), (margin, 50))
        for x in range(math.ceil(-width / 2), math.floor(width / 2) + 1, 2):
            pygame.draw.line(surface, (219, 216, 205), point(x, -depth / 2), point(x, depth / 2))
        for z in range(math.ceil(-depth / 2), math.floor(depth / 2) + 1, 2):
            pygame.draw.line(surface, (219, 216, 205), point(-width / 2, z), point(width / 2, z))
        for box in level.collision_boxes:
            bottom, top = box.collider.bottom, box.collider.top
            if bottom < height + 2 and top > height + 0.22:
                polygon(surface, box, (55, 69, 71) if box.size[1] > 1.2 else (143, 151, 143))
        for obj in level.objects:
            if obj.entity is not None:
                continue
            for box in obj.boxes:
                if box.collider.bottom < height + 2 and box.collider.top > height + 0.22:
                    polygon(surface, box, (55, 69, 71))
        labels = []
        for obj in level.objects:
            if "open" not in obj.states:
                continue
            panel = obj.states["default"].boxes[0]
            if abs(panel.position[1] - panel.size[1] / 2 - height - 0.02) > 0.01:
                continue
            number = len(labels) + 1
            labels.append(f"{number}. {obj.states['default'].interaction.name}")
            polygon(surface, panel, (199, 110, 44))
            polygon(surface, obj.states["open"].boxes[0], (48, 137, 112))
            label = font.render(str(number), True, (119, 45, 24))
            surface.blit(label, point(panel.position[0] + 0.35, panel.position[2] + 0.35))
        if floor == 0:
            from game.levels.hospital import ROOM_NAMES
            for index, name in enumerate(ROOM_NAMES):
                label = font.render(name, True, (30, 45, 47), (237, 234, 223))
                surface.blit(label, label.get_rect(center=point(-17.5 + index * 7, -13.1)))
            for obj in level.objects:
                if obj.name in ("main_entrance_0", "side_entrance_0"):
                    for box in obj.boxes:
                        polygon(surface, box, (54, 112, 157))
        image_path = output_dir / f"floor_{floor + 1}.png"
        pygame.image.save(surface, image_path)
        (output_dir / f"floor_{floor + 1}_doors.txt").write_text("\n".join(labels), encoding="utf-8")
        print(image_path.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="artifacts/plans")
    parser.add_argument("--level", choices=("start", "peaceful"), default="start")
    args = parser.parse_args()
    export_plans(args.output_dir, args.level)
