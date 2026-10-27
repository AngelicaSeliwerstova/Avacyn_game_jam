from dataclasses import dataclass, replace
import math

from engine.scene.box import Box
from engine.scene.lighting import PointLight, validate_rgb


@dataclass(frozen=True)
class BasementLayout:
    depth: float
    entry: tuple[int, int, int]
    lower_row: int
    lamp_columns: int
    lamp_rows: int
    lamp_margin: float
    lamp_color: tuple[float, float, float]
    lamp_intensity: float
    lamp_radius: float
    boxes: tuple[Box, ...] = ()

    def __post_init__(self):
        for value in (self.depth, self.lamp_margin, self.lamp_intensity, self.lamp_radius):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("Basement dimensions and lamp parameters must be positive")
        if any(not isinstance(n, int) or n < 2 for n in (self.lamp_columns, self.lamp_rows)):
            raise ValueError("Basement lamp grid needs at least two rows and columns")
        validate_rgb(self.lamp_color)

    def stair_points(self, layout):
        upper = layout.position(self.entry)
        z = (self.lower_row + 0.5) * layout.cell_size - layout.depth / 2
        x = -(layout.width + layout.wing_width) / 2
        return ((upper[0], -self.depth, z), (x, -self.depth, z),
                (x, 0.0, upper[2]), upper)

    def lights(self, layout):
        y = -layout.slab_thickness - 0.24
        return tuple(PointLight((
            -layout.width / 2 + self.lamp_margin + column * (layout.width - 2 * self.lamp_margin)
            / (self.lamp_columns - 1), y,
            -layout.depth / 2 + self.lamp_margin + row * (layout.depth - 2 * self.lamp_margin)
            / (self.lamp_rows - 1),
        ), self.lamp_color, self.lamp_intensity, self.lamp_radius)
                     for row in range(self.lamp_rows) for column in range(self.lamp_columns))


def build_basement_room(layout, boxes):
    """Прямоугольный зал с потолочным светом и блоками из описания карты."""
    spec = layout.basement
    bottom, ceiling = -spec.depth, -layout.slab_thickness
    height = ceiling - bottom
    wall = layout.wall_thickness
    y = (bottom + ceiling) / 2
    for z in (-layout.depth / 2 + wall / 2, layout.depth / 2 - wall / 2):
        boxes.append(Box((0, y, z), (layout.width, height, wall), material="concrete"))
    boxes.append(Box(((layout.width - wall) / 2, y, 0), (wall, height, layout.depth), material="concrete"))
    doorway = spec.stair_points(layout)[0][2]
    for start, end in ((-layout.depth / 2, doorway - layout.cell_size / 2),
                       (doorway + layout.cell_size / 2, layout.depth / 2)):
        boxes.append(Box((-(layout.width - wall) / 2, y, (start + end) / 2),
                         (wall, height, end - start), material="concrete"))
    # Сплошной пол первого этажа служит потолком подвала.
    boxes.append(Box((0, -layout.slab_thickness / 2, 0),
                     (layout.width, layout.slab_thickness, layout.depth), material=layout.floor_materials[0]))
    # Нижняя бетонная облицовка отделяет потолок зала от плитки пола над ним.
    boxes.append(Box((0, -layout.slab_thickness - 0.01, 0),
                     (layout.width, 0.02, layout.depth), material="concrete"))
    for box in spec.boxes:
        x, y, z = box.position
        boxes.append(replace(box, position=(x, bottom + y, z)))
