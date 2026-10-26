from array import array
from dataclasses import dataclass
import math

from engine.rendering.visibility import distance_to_box_squared
from engine.scene.level import Level


@dataclass(frozen=True)
class LightGrid:
    origin: tuple[float, float, float]
    shape: tuple[int, int, int]
    cell_size: float
    max_lights: int
    indices: bytes

    @property
    def texture_size(self):
        return self.max_lights + 1, math.prod(self.shape)


def build_light_grid(level: Level, cell_size: float, max_cells: int) -> LightGrid | None:
    if level.lighting is None or len(level.lighting.lights) <= 16:
        return None
    width, depth = level.floor_size
    points = [(-width / 2, 0, -depth / 2), (width / 2, 0, depth / 2)]
    for box in level.boxes + level.decorations:
        points.extend(tuple(p + sign * size / 2 for p, size in zip(box.position, box.size))
                      for sign in (-1, 1))
    origin = tuple(min(point[axis] for point in points) for axis in range(3))
    maximum = tuple(max(point[axis] for point in points) for axis in range(3))
    shape = tuple(max(1, math.ceil((high - low) / cell_size)) for low, high in zip(origin, maximum))
    if math.prod(shape) > max_cells:
        return None
    cells = []
    half_size = (cell_size / 2,) * 3
    for z in range(shape[2]):
        for y in range(shape[1]):
            for x in range(shape[0]):
                center = tuple(low + (index + 0.5) * cell_size for low, index in zip(origin, (x, y, z)))
                # Порядок сохраняется: сложение вкладов ламп совпадает с исходным шейдером.
                indices = tuple(index for index, light in enumerate(level.lighting.lights)
                                if distance_to_box_squared(light.position, center, half_size)
                                <= (light.radius + 0.001) ** 2)
                cells.append(indices)
    maximum_count = max(map(len, cells), default=0)
    data = array("i")
    for indices in cells:
        data.extend((len(indices), *indices, *([0] * (maximum_count - len(indices)))))
    return LightGrid(origin, shape, cell_size, maximum_count, data.tobytes())
