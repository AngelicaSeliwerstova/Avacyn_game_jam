"""Широкая винтовая лестница из повёрнутых блоков с настоящими коллайдерами."""

from dataclasses import dataclass
import math

from engine.scene.box import Box


@dataclass(frozen=True)
class SpiralStair:
    center: tuple[float, float] = (-13.0, 4.0)
    inner_radius: float = 1.55
    outer_radius: float = 4.2
    height: float = 4.8
    steps: int = 36

    def __post_init__(self):
        if (len(self.center) != 2 or not all(math.isfinite(v) for v in self.center)
                or not all(math.isfinite(v) for v in (self.inner_radius, self.outer_radius, self.height))
                or self.inner_radius <= 0 or self.outer_radius <= self.inner_radius
                or self.height <= 0 or not isinstance(self.steps, int) or self.steps < 12):
            raise ValueError("Invalid spiral stair dimensions")

    def point(self, angle: float, radius: float, height: float = 0.0):
        angle = math.radians(angle)
        return (self.center[0] + radius * math.cos(angle), height,
                self.center[1] + radius * math.sin(angle))

    def walking_path(self):
        radius = (self.inner_radius + self.outer_radius) / 2
        delta = 360 / self.steps
        return tuple(self.point(90 - (i + 0.5) * delta, radius, (i + 1) * self.height / self.steps)
                     for i in range(self.steps))

    def build(self) -> tuple[Box, ...]:
        boxes = []
        delta = 360 / self.steps
        rise = self.height / self.steps
        strips = 6
        strip_width = (self.outer_radius - self.inner_radius) / strips
        for step in range(self.steps):
            angle = 90 - (step + 0.5) * delta
            top = (step + 1) * rise
            # Радиальные полосы заполняют сектор, не создавая прямоугольных углов во всём проёме.
            for strip in range(strips):
                radius = self.inner_radius + (strip + 0.5) * strip_width
                depth = 2 * (radius + strip_width / 2) * math.tan(math.radians(delta / 2)) + 0.015
                boxes.append(Box(self.point(angle, radius, top - 0.11),
                                 (strip_width + 0.012, 0.22, depth),
                                 material="concrete", yaw_degrees=-angle))
            # Сплошной внутренний парапет подчёркивает открытый лестничный колодец.
            radius = self.inner_radius - 0.09
            depth = 2 * radius * math.tan(math.radians(delta / 2)) + 0.045
            boxes.append(Box(self.point(angle, radius, top + 0.38), (0.18, 1.0, depth),
                             material="plaster", yaw_degrees=-angle))
            boxes.append(Box(self.point(angle, radius, top + 0.91), (0.23, 0.07, depth + 0.02),
                             material="rust", yaw_degrees=-angle, color=(0.25, 0.24, 0.22)))
            # Нижний вход оставляем свободным с внешней стороны первых ступеней.
            if step >= 3:
                radius = self.outer_radius + 0.025
                depth = 2 * radius * math.tan(math.radians(delta / 2)) + 0.025
                boxes.append(Box(self.point(angle, radius, top + 1.0), (0.075, 0.075, depth),
                                 material="rust", yaw_degrees=-angle, color=(0.26, 0.25, 0.23)))
                if step % 2 == 0:
                    boxes.append(Box(self.point(angle, radius, top + 0.47), (0.06, 1.0, 0.06),
                                     material="rust", color=(0.28, 0.27, 0.25)))
        # Верхний выход идёт по касательной вправо; под ним свободно начало марша.
        cx, cz = self.center
        boxes.append(Box((cx + 3.0, self.height - 0.12, cz + 2.9),
                         (6.0, 0.24, 2.65), material="concrete"))
        return tuple(boxes)
