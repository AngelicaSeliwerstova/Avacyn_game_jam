"""Мебель и небольшие детали больницы, собранные из геометрии движка."""

import math

from engine.scene.box import Box


class HospitalProps:
    def __init__(self):
        self.boxes = []
        self.decorations = []

    def part(self, x, z, offset, size, material="wood", color=None, yaw=0, detail=False):
        dx, y, dz = offset
        item = Box((x + dx, y, z + dz), size, material=material, color=color,
                   local_texture=material == "wood").rotated_around((x, 0, z), yaw)
        (self.decorations if detail else self.boxes).append(item)
        return item

    def sofa(self, x, z, width=2.6, yaw=0):
        leather = (0.29, 0.12, 0.09)
        self.part(x, z, (0, 0.35, 0), (width, 0.35, 0.92), "wood", yaw=yaw)
        self.part(x, z, (0, 0.9, 0.4), (width, 0.85, 0.2), color=leather, yaw=yaw)
        seats = max(2, round(width / 0.8))
        for i in range(seats):
            dx = (i + 0.5) * (width - 0.3) / seats - (width - 0.3) / 2
            self.part(x, z, (dx, 0.59, -0.05), ((width - 0.38) / seats, 0.17, 0.76),
                      color=(0.35, 0.16, 0.12), yaw=yaw)
            self.part(x, z, (dx, 0.95, 0.26), ((width - 0.38) / seats, 0.57, 0.09),
                      color=(0.31, 0.14, 0.105), yaw=yaw, detail=True)
        for side in (-1, 1):
            self.part(x, z, (side * (width / 2 - 0.09), 0.65, 0), (0.22, 0.65, 1.03),
                      color=leather, yaw=yaw)

    def table(self, x, z, width=1.8, depth=0.8, height=0.6, yaw=0):
        self.part(x, z, (0, height - 0.05, 0), (width, 0.1, depth), yaw=yaw)
        for dx in (-width / 2 + 0.12, width / 2 - 0.12):
            for dz in (-depth / 2 + 0.12, depth / 2 - 0.12):
                self.part(x, z, (dx, (height - 0.1) / 2, dz), (0.09, height - 0.1, 0.09), yaw=yaw)
        self.part(x, z, (-width * 0.2, height + 0.015, 0), (0.32, 0.025, 0.24),
                  color=(0.7, 0.67, 0.52), yaw=yaw, detail=True)

    def chair(self, x, z, yaw=0):
        self.part(x, z, (0, 0.48, 0), (0.58, 0.13, 0.58), color=(0.27, 0.34, 0.3), yaw=yaw)
        self.part(x, z, (0, 0.85, 0.24), (0.58, 0.62, 0.1), color=(0.27, 0.34, 0.3), yaw=yaw)
        for dx in (-0.23, 0.23):
            self.part(x, z, (dx, 0.22, 0), (0.055, 0.44, 0.48), "rust", yaw=yaw)

    def plant(self, x, z, small=False, base=0):
        scale = 0.4 if small else 1.0
        self.part(x, z, (0, base + 0.22 * scale, 0), (0.48 * scale, 0.44 * scale, 0.48 * scale),
                  color=(0.29, 0.25, 0.18), detail=small)
        self.part(x, z, (0, base + 0.45 * scale, 0), (0.57 * scale, 0.1 * scale, 0.57 * scale),
                  color=(0.38, 0.32, 0.23), detail=True)
        self.part(x, z, (0, base + 0.78 * scale, 0), (0.07 * scale, 0.75 * scale, 0.07 * scale),
                  color=(0.23, 0.25, 0.12), detail=True)
        for i in range(9):
            angle = i * 137.5
            rad = math.radians(angle)
            reach = (0.22 if i < 6 else 0.14) * scale
            self.part(x, z, (reach * math.sin(rad), base + (0.8 + i * 0.055) * scale,
                             reach * math.cos(rad)),
                      (0.18 * scale, 0.12 * scale, 0.6 * scale),
                      color=(0.17 + (i % 3) * 0.035, 0.27 + (i % 2) * 0.05, 0.12),
                      yaw=angle, detail=True)

    def cabinet(self, x, z, width=1.2, height=2.0, yaw=0, medical=True):
        color = (0.48, 0.55, 0.5) if medical else None
        self.part(x, z, (0, height / 2, 0), (width, height, 0.62), "rust" if medical else "wood",
                  color, yaw)
        for side in (-1, 1):
            self.part(x, z, (side * width / 4, height * 0.58, -0.325),
                      (width / 2 - 0.05, height * 0.77, 0.025),
                      "rust", (0.54, 0.6, 0.55) if medical else (0.29, 0.24, 0.17), yaw, True)
            self.part(x, z, (side * 0.08, height * 0.56, -0.36), (0.025, 0.18, 0.04),
                      "rust", (0.18, 0.19, 0.17), yaw, True)

    def cart(self, x, z):
        for y in (0.28, 0.86):
            self.part(x, z, (0, y, 0), (0.7, 0.055, 0.48), "rust", (0.56, 0.59, 0.54))
        for dx in (-0.3, 0.3):
            for dz in (-0.19, 0.19):
                self.part(x, z, (dx, 0.47, dz), (0.035, 0.85, 0.035), "rust")
        for i in range(3):
            self.part(x, z, ((i - 1) * 0.18, 0.97, 0), (0.09, 0.18, 0.09),
                      color=(0.66, 0.71, 0.6), detail=True)

    def desk_details(self, x, z, height=0.98):
        self.part(x, z, (0.25, height + 0.24, 0.1), (0.62, 0.46, 0.09),
                  "rust", (0.12, 0.15, 0.14), detail=True)
        self.part(x, z, (0.25, height + 0.24, 0.045), (0.51, 0.34, 0.018),
                  color=(0.25, 0.34, 0.3), detail=True)
        self.part(x, z, (0.25, height + 0.04, -0.18), (0.53, 0.04, 0.18),
                  "rust", (0.21, 0.24, 0.21), detail=True)
        self.part(x, z, (-0.55, height + 0.035, -0.04), (0.37, 0.055, 0.29),
                  color=(0.7, 0.68, 0.57), detail=True)

    def radiator(self, x, z):
        for i in range(9):
            self.part(x, z, ((i - 4) * 0.13, 0.57, 0), (0.09, 0.7, 0.18),
                      "rust", (0.48, 0.51, 0.45))
