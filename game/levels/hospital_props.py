"""Мебель и небольшие детали больницы, собранные из геометрии движка."""

import math
from functools import wraps
from dataclasses import replace
from contextlib import contextmanager

from engine.scene.box import Box
from engine.scene.interaction import Interaction


def authored_prop(method):
    @wraps(method)
    def build(self, x, z, *args, **kwargs):
        with self.authored_group(method.__name__, x, z):
            return method(self, x, z, *args, **kwargs)
    return build


class HospitalProps:
    def __init__(self):
        self.boxes = []
        self.decorations = []
        self._group_counts = {}

    @contextmanager
    def authored_group(self, name, x, z, extra_boxes=None):
        key = f"{name}:{x:.4f}:{z:.4f}"
        count = self._group_counts.get(key, 0)
        self._group_counts[key] = count + 1
        group = f"{key}:{count}"
        sources = [self.boxes, self.decorations]
        if extra_boxes is not None:
            sources.append(extra_boxes)
        starts = [len(source) for source in sources]
        yield
        for source, start in zip(sources, starts):
            for index in range(start, len(source)):
                source[index] = replace(source[index], authored_group=group)


    @contextmanager
    def against_wall(self, axis, surface, inward=1, gap=0.06, extra_boxes=None):
        """Align an entire furniture assembly, including handles and feet."""
        sources = [self.boxes, self.decorations]
        if extra_boxes is not None:
            sources.append(extra_boxes)
        starts = [len(source) for source in sources]
        yield
        items = [item for source, start in zip(sources, starts) for item in source[start:]]
        if not items:
            return
        coordinate = 0 if axis == "x" else 2
        edges = [item.position[coordinate] - inward * item.bounds_half_size[coordinate] for item in items]
        edge = min(edges) if inward > 0 else max(edges)
        shift = surface + inward * gap - edge
        for source, start in zip(sources, starts):
            for index in range(start, len(source)):
                point = list(source[index].position)
                point[coordinate] += shift
                source[index] = replace(source[index], position=tuple(point))

    @contextmanager
    def rotated_group(self, x, z, yaw, extra_boxes=None):
        sources = [self.boxes, self.decorations]
        if extra_boxes is not None:
            sources.append(extra_boxes)
        starts = [len(source) for source in sources]
        yield
        for source, start in zip(sources, starts):
            for index in range(start, len(source)):
                source[index] = source[index].rotated_around((x, 0, z), yaw)

    def part(self, x, z, offset, size, material=None, color=None, yaw=0, detail=False):
        dx, y, dz = offset
        item = Box((x + dx, y, z + dz), size, material=material, color=color,
                   local_texture=material in {"wood", "furniture_wood", "sofa_fabric", "chair_fabric",
                                              "bed_linen", "bed_blanket", "privacy_fabric"}).rotated_around((x, 0, z), yaw)
        (self.decorations if detail else self.boxes).append(item)
        return item

    @authored_prop
    def sofa(self, x, z, width=2.6, yaw=0):
        leather = (0.29, 0.12, 0.09)
        self.part(x, z, (0, 0.35, 0), (width, 0.35, 0.92), "sofa_fabric", yaw=yaw)
        self.part(x, z, (0, 0.9, 0.4), (width, 0.85, 0.2), "sofa_fabric", color=leather, yaw=yaw)
        seats = max(2, round(width / 0.8))
        for i in range(seats):
            dx = (i + 0.5) * (width - 0.3) / seats - (width - 0.3) / 2
            self.part(x, z, (dx, 0.59, -0.05), ((width - 0.38) / seats, 0.17, 0.76),
                      "sofa_fabric", color=(0.35, 0.16, 0.12), yaw=yaw)
            self.part(x, z, (dx, 0.95, 0.26), ((width - 0.38) / seats, 0.57, 0.09),
                      "sofa_fabric", color=(0.31, 0.14, 0.105), yaw=yaw, detail=True)
        for side in (-1, 1):
            self.part(x, z, (side * (width / 2 - 0.09), 0.65, 0), (0.22, 0.65, 1.03),
                      "sofa_fabric", color=leather, yaw=yaw)

    @authored_prop
    def table(self, x, z, width=1.8, depth=0.8, height=0.6, yaw=0):
        self.part(x, z, (0, height - 0.05, 0), (width, 0.1, depth), "furniture_wood", yaw=yaw)
        for dx in (-width / 2 + 0.12, width / 2 - 0.12):
            for dz in (-depth / 2 + 0.12, depth / 2 - 0.12):
                self.part(x, z, (dx, (height - 0.1) / 2, dz), (0.09, height - 0.1, 0.09), "furniture_wood", yaw=yaw)
        self.part(x, z, (-width * 0.2, height + 0.015, 0), (0.32, 0.025, 0.24),
                  color=(0.7, 0.67, 0.52), yaw=yaw, detail=True)

    @authored_prop
    def chair(self, x, z, yaw=0):
        self.part(x, z, (0, 0.48, 0), (0.58, 0.13, 0.58), "chair_fabric", color=(0.27, 0.34, 0.3), yaw=yaw)
        self.part(x, z, (0, 0.85, 0.24), (0.58, 0.62, 0.1), "chair_fabric", color=(0.27, 0.34, 0.3), yaw=yaw)
        for dx in (-0.23, 0.23):
            self.part(x, z, (dx, 0.22, 0), (0.055, 0.44, 0.48), "rust", yaw=yaw)

    @authored_prop
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

    @authored_prop
    def cabinet(self, x, z, width=1.2, height=2.0, yaw=0, medical=True):
        color = (0.48, 0.55, 0.5) if medical else None
        self.part(x, z, (0, height / 2, 0), (width, height, 0.62), "medical_enamel" if medical else "furniture_wood",
                  color, yaw)
        for side in (-1, 1):
            self.part(x, z, (side * width / 4, height * 0.58, -0.325),
                      (width / 2 - 0.05, height * 0.77, 0.025),
                      "medical_enamel" if medical else "furniture_wood",
                      (0.54, 0.6, 0.55) if medical else (0.29, 0.24, 0.17), yaw, True)
            self.part(x, z, (side * 0.08, height * 0.56, -0.36), (0.025, 0.18, 0.04),
                      "brushed_metal", (0.18, 0.19, 0.17), yaw, True)

    @authored_prop
    def cart(self, x, z):
        for y in (0.28, 0.86):
            self.part(x, z, (0, y, 0), (0.7, 0.055, 0.48), "rust", (0.56, 0.59, 0.54))
        for dx in (-0.3, 0.3):
            for dz in (-0.19, 0.19):
                self.part(x, z, (dx, 0.47, dz), (0.035, 0.85, 0.035), "rust")
                self.part(x, z, (dx, 0.045, dz), (0.09, 0.09, 0.06),
                          "rust", (0.18, 0.21, 0.19), detail=True)
        for i in range(3):
            self.part(x, z, ((i - 1) * 0.18, 0.97, 0), (0.09, 0.18, 0.09),
                      color=(0.66, 0.71, 0.6), detail=True)

    @authored_prop
    def desk_details(self, x, z, height=0.98):
        self.part(x, z, (0.25, height + 0.24, 0.1), (0.62, 0.46, 0.09),
                  "rust", (0.12, 0.15, 0.14), detail=True)
        self.part(x, z, (0.25, height + 0.24, 0.045), (0.51, 0.34, 0.018),
                  color=(0.25, 0.34, 0.3), detail=True)
        self.part(x, z, (0.25, height + 0.04, -0.18), (0.53, 0.04, 0.18),
                  "rust", (0.21, 0.24, 0.21), detail=True)
        self.part(x, z, (-0.55, height + 0.035, -0.04), (0.37, 0.055, 0.29),
                  color=(0.7, 0.68, 0.57), detail=True)

    @authored_prop
    def radiator(self, x, z):
        for i in range(9):
            self.part(x, z, ((i - 4) * 0.13, 0.57, 0), (0.09, 0.7, 0.18),
                      "rust", (0.48, 0.51, 0.45))

    @authored_prop
    def bed_details(self, x, z, mattress_top=0.655):
        self.part(x, z, (0, mattress_top + 0.09, -0.64), (0.77, 0.17, 0.43),
                  "bed_linen", color=(0.75, 0.75, 0.65), detail=True)
        self.part(x, z, (0, mattress_top + 0.025, 0.42), (1.03, 0.045, 0.93),
                  "bed_blanket", color=(0.25, 0.36, 0.32), detail=True)
        for side in (-1, 1):
            self.part(x, z, (side * 0.57, mattress_top + 0.13, 0.18), (0.025, 0.035, 1.2),
                      "brushed_metal", (0.47, 0.5, 0.44), detail=True)

    @authored_prop
    def iv_stand(self, x, z):
        self.part(x, z, (0, 0.83, 0), (0.045, 1.66, 0.045), "rust", (0.5, 0.55, 0.52))
        for yaw in (0, 90):
            self.part(x, z, (0, 0.07, 0), (0.45, 0.06, 0.055), "rust", yaw=yaw, detail=True)
        self.part(x, z, (0, 1.72, 0), (0.42, 0.035, 0.035), "rust", detail=True)
        self.part(x, z, (0.15, 1.49, 0), (0.14, 0.28, 0.065),
                  color=(0.65, 0.72, 0.64), detail=True)
        self.part(x, z, (0.15, 1.1, 0), (0.012, 0.55, 0.012),
                  color=(0.48, 0.59, 0.53), detail=True)

    @authored_prop
    def monitor(self, x, z, yaw=0):
        self.part(x, z, (0, 0.48, 0), (0.64, 0.85, 0.5), "medical_enamel", (0.34, 0.43, 0.4), yaw)
        self.part(x, z, (0, 1.13, 0), (0.67, 0.46, 0.17), "medical_enamel", (0.16, 0.2, 0.19), yaw)
        for dx in (-0.23, 0.23):
            for dz in (-0.16, 0.16):
                self.part(x, z, (dx, 0.04, dz), (0.1, 0.08, 0.065),
                          "rust", (0.18, 0.21, 0.19), yaw, True)
        self.part(x, z, (-0.05, 1.14, -0.095), (0.45, 0.3, 0.02),
                  color=(0.1, 0.25, 0.2), yaw=yaw, detail=True)
        for dx, dy in ((-0.17, 0), (-0.09, 0), (-0.03, 0.07), (0.03, -0.04), (0.1, 0)):
            self.part(x, z, (dx, 1.14 + dy, -0.11), (0.065, 0.018, 0.012),
                      color=(0.36, 0.62, 0.41), yaw=yaw, detail=True)

    @authored_prop
    def linen_shelf(self, x, z, width=2.0, yaw=0):
        for dx in (-width / 2 + 0.04, width / 2 - 0.04):
            self.part(x, z, (dx, 1, 0), (0.07, 2, 0.55), "rust", yaw=yaw)
        for y in (0.18, 0.7, 1.22, 1.74):
            self.part(x, z, (0, y, 0), (width, 0.055, 0.55), "rust", yaw=yaw)
            for dx in (-width / 4, width / 4):
                self.part(x, z, (dx, y + 0.14, 0), (width / 2 - 0.16, 0.22, 0.44),
                          "bed_linen", color=(0.63, 0.66, 0.56), yaw=yaw, detail=True)

    @authored_prop
    def sink(self, x, z, yaw=0):
        self.part(x, z, (0, 0.45, 0), (0.75, 0.9, 0.5), "medical_enamel", (0.49, 0.56, 0.51), yaw)
        self.part(x, z, (0, 0.94, 0), (0.84, 0.12, 0.57), "ceramic", color=(0.68, 0.71, 0.63), yaw=yaw)
        self.part(x, z, (0, 1.005, -0.03), (0.49, 0.012, 0.32),
                  color=(0.32, 0.41, 0.38), yaw=yaw, detail=True)
        self.part(x, z, (0, 1.12, 0.2), (0.045, 0.27, 0.045), "rust", yaw=yaw, detail=True)
        self.part(x, z, (0, 1.24, 0.12), (0.045, 0.04, 0.2), "rust", yaw=yaw, detail=True)

    @authored_prop
    def privacy_screen(self, x, z, yaw=0, width=2.0):
        self.part(x, z, (0, 1.22, 0), (width, 1.6, 0.045),
                  "privacy_fabric", color=(0.35, 0.48, 0.41), yaw=yaw)
        for dx in (-width / 2, width / 2):
            self.part(x, z, (dx, 1.06, 0), (0.035, 2.1, 0.035), "rust", yaw=yaw)
            self.part(x, z, (dx, 0.06, 0), (0.075, 0.055, 0.5), "rust", yaw=yaw)
        for dx in (-width / 3, 0, width / 3):
            self.part(x, z, (dx, 1.22, -0.028), (0.025, 1.5, 0.015),
                      "privacy_fabric", color=(0.29, 0.41, 0.35), yaw=yaw, detail=True)

    @authored_prop
    def sign(self, x, z, text, yaw=0, width=1.05):
        board = self.part(x, z, (0, 1.72, 0), (width, 0.36, 0.035),
                          "rust", (0.21, 0.32, 0.29), yaw, True)
        self.decorations[-1] = replace(board, interaction=Interaction(text, text, "Прочитать"))
        for dx in (-0.24, 0, 0.24):
            self.part(x, z, (dx, 1.72, -0.025), (0.13, 0.045, 0.012),
                      color=(0.72, 0.75, 0.63), yaw=yaw, detail=True)
