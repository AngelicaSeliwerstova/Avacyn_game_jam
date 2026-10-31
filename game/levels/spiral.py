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
    flights: int = 2
    landing_steps: int = 6

    def __post_init__(self):
        if (len(self.center) != 2 or not all(math.isfinite(v) for v in self.center)
                or not all(math.isfinite(v) for v in (self.inner_radius, self.outer_radius, self.height))
                or self.inner_radius <= 0 or self.outer_radius <= self.inner_radius
                or self.height <= 0 or not isinstance(self.steps, int) or self.steps < 12
                or not isinstance(self.flights, int) or self.flights < 1
                or not isinstance(self.landing_steps, int) or not 0 <= self.landing_steps < self.steps - 6):
            raise ValueError("Invalid spiral stair dimensions")

    @property
    def total_height(self):
        return self.height * self.flights

    @property
    def gallery_radius(self):
        # Keep gallery walls outside the stair handrail, including rotated corners.
        return self.outer_radius + 0.32

    @property
    def gallery_drop(self):
        return 1.1

    def step_height(self, index):
        flight, step = divmod(index, self.steps)
        return flight * self.height + max(0, step + 1 - self.landing_steps) * (
            self.height / (self.steps - self.landing_steps))

    def point(self, angle: float, radius: float, height: float = 0.0):
        angle = math.radians(angle)
        return (self.center[0] + radius * math.cos(angle), height,
                self.center[1] + radius * math.sin(angle))

    def walking_path(self):
        radius = (self.inner_radius + self.outer_radius) / 2
        delta = 360 / self.steps
        return tuple(self.point(90 - (i + 0.5) * delta, radius, self.step_height(i))
                     for i in range(self.steps * self.flights))

    def build(self) -> tuple[Box, ...]:
        boxes = []
        delta = 360 / self.steps
        strips = 6
        strip_width = (self.outer_radius - self.inner_radius) / strips

        def parapet(step, radius, material):
            angle = 90 - (step + 0.5) * delta
            top = self.step_height(step)
            next_top = self.step_height(step + 1) if step + 1 < self.steps * self.flights else top
            depth = 2 * (radius + 0.13) * math.tan(math.radians(delta / 2)) + 0.04
            boxes.append(Box(self.point(angle, radius, top + 0.53), (0.2, 1.1, depth),
                             material=material, yaw_degrees=-angle))
            # Поручень набирается с малым перепадом высоты: соседние части
            # перекрываются, вместо отдельных горизонтальных планок над ступенями.
            for part in range(2):
                fraction = (part + 0.5) / 2
                cap_angle = 90 - (step + fraction) * delta
                cap_height = top + (next_top - top) * fraction + 0.99
                cap_depth = 2 * (radius + 0.13) * math.tan(math.radians(delta / 4)) + 0.035
                boxes.append(Box(self.point(cap_angle, radius, cap_height), (0.26, 0.16, cap_depth),
                                 material="rust", yaw_degrees=-cap_angle, color=(0.25, 0.24, 0.22)))

        for step in range(self.steps * self.flights):
            angle = 90 - (step + 0.5) * delta
            top = self.step_height(step)
            # Радиальные полосы заполняют сектор, не создавая прямоугольных углов во всём проёме.
            for strip in range(strips if step >= self.landing_steps else 0):
                radius = self.inner_radius + (strip + 0.5) * strip_width
                depth = 2 * (radius + strip_width / 2) * math.tan(math.radians(delta / 2)) + 0.015
                boxes.append(Box(self.point(angle, radius, top - 0.11),
                                 (strip_width + 0.012, 0.22, depth),
                                 material="concrete", yaw_degrees=-angle))
            # Сплошной внутренний парапет подчёркивает открытый лестничный колодец.
            parapet(step, self.inner_radius - 0.09, "plaster")
            # Нижний вход оставляем свободным с внешней стороны первых ступеней.
            remaining = self.steps - 1 - step % self.steps
            merge_height = remaining * self.height / (self.steps - self.landing_steps)
            if step % self.steps >= self.landing_steps and merge_height > self.gallery_drop:
                parapet(step, self.outer_radius + 0.025, "plaster")
        # Верхний выход идёт по касательной вправо; под ним свободно начало марша.
        cx, cz = self.center
        for flight in range(1, self.flights + 1):
            boxes.append(Box((cx + 3.0, flight * self.height - 0.12, cz + 2.9),
                             (6.0, 0.24, 2.65), material="concrete"))
        # The final flight ends here: protect the exposed inner edge of its bridge.
        # Intermediate landings remain open so the next flight stays accessible.
        start = cx
        end = cx + math.sqrt(self.gallery_radius ** 2 - (self.inner_radius - 0.09) ** 2)
        z = cz + self.inner_radius - 0.09
        boxes.append(Box(((start + end) / 2, self.total_height + 0.53, z),
                         (end - start, 1.1, 0.2), material="plaster"))
        boxes.append(Box(((start + end) / 2, self.total_height + 0.99, z),
                         (end - start + 0.08, 0.16, 0.26), material="rust",
                         color=(0.25, 0.24, 0.22)))
        return tuple(boxes)
