from pathlib import Path

from config import settings
from engine.scene.box import Box
from engine.scene.level import Level
from engine.scene.lighting import Lighting, PointLight
from game.levels.basement import build_basement_room
from game.levels.maze_layout import MazeLayout, StairLink, load_maze_layout


def maze_layout_path() -> Path:
    return Path(__file__).resolve().parents[2] / "resources" / "levels" / settings.MAZE_LAYOUT


def create_maze_level() -> Level:
    layout = load_maze_layout(maze_layout_path())
    boxes = []
    cell = layout.cell_size
    thickness = layout.slab_thickness
    roof_y = layout.floor_height + layout.wall_height

    for floor, rows in enumerate(layout.floors):
        base = floor * layout.floor_height
        materials = layout.wall_materials[floor]
        for row, cells in enumerate(rows):
            start = 0
            while start < len(cells):
                if cells[start] != "#":
                    start += 1
                    continue
                end = start + 1
                while end < len(cells) and cells[end] == "#":
                    end += 1
                # Соседние стеновые клетки объединяются в один блок.
                boxes.append(Box(
                    ((start + end) * cell / 2 - layout.width / 2,
                     base + layout.wall_height / 2, (row + 0.5) * cell - layout.depth / 2),
                    ((end - start) * cell, layout.wall_height, cell),
                    material=materials[min(len(materials) - 1, row * len(materials) // len(rows))],
                ))
                start = end

    boxes.extend((
        Box((0, layout.floor_height - thickness / 2, 0), (layout.width, thickness, layout.depth),
            material=layout.floor_materials[1]),
        Box((0, roof_y + thickness / 2, 0), (layout.width, thickness, layout.depth), material="concrete"),
    ))
    for link in layout.stairs:
        _build_stair_wing(layout, link, boxes)
    if layout.basement is not None:
        build_basement_room(layout, boxes)
        spec = layout.basement
        _build_stair_wing(layout, StairLink("B1", "west", spec.lower_row, spec.entry[1]), boxes,
                          points=spec.stair_points(layout))

    # Выход ведёт на ограждённый балкон второго этажа.
    goal_x, goal_y, goal_z = layout.goal_position
    boxes.append(Box((goal_x, goal_y - thickness / 2, goal_z),
                     (cell, thickness, layout.balcony_depth), material="concrete"))
    rail = layout.rail_thickness
    guard = layout.rail_height + 0.2
    for side in (-1, 1):
        boxes.append(Box((goal_x + side * (cell - rail) / 2, goal_y + guard / 2, goal_z),
                         (rail, guard, layout.balcony_depth), material="rust"))
    boxes.append(Box((goal_x, goal_y + guard / 2, goal_z - (layout.balcony_depth - rail) / 2),
                     (cell, guard, rail), material="rust"))
    # Ржавая рама отличает выход от обычного прохода.
    frame_z = -layout.depth / 2 - rail
    for side in (-1, 1):
        boxes.append(Box((goal_x + side * cell * 0.4, goal_y + 1.3, frame_z),
                         (rail, 2.6, rail * 2), material="rust"))
    boxes.append(Box((goal_x, goal_y + 2.6, frame_z), (cell * 0.8, rail, rail * 2), material="rust"))

    x, y, z = layout.position(layout.spawn)
    decorations = []
    lighting = layout.lighting
    if layout.lighting is not None:
        for light in layout.lighting.lights:
            ceiling = roof_y if abs(light.position[0]) > layout.width / 2 else (
                layout.wall_height + (layout.floor_height if light.position[1] > layout.floor_height else 0)
            )
            _build_lamp(light, ceiling, decorations)
        if layout.basement is not None:
            lights = layout.basement.lights(layout)
            for index, light in enumerate(lights):
                _build_lamp(light, -thickness, decorations, rotated=bool(index % 2))
            extra = []
            for point in layout.basement.stair_points(layout)[1:3]:
                px, py, pz = point
                light = PointLight((px, py + layout.wall_height - 0.24, pz), (1.0, 0.65, 0.35), 2.6, 6.0)
                _build_lamp(light, layout.wall_height, decorations)
                extra.append(light)
            lighting = Lighting(lighting.ambient, lighting.lights + lights + tuple(extra), lighting.shadow_resolution)
    underground = layout.basement is not None
    return Level(
        floor_size=(layout.width + 2 * layout.wing_width, layout.depth + 2 * layout.balcony_depth),
        floor_tile_size=settings.FLOOR_TILE_SIZE,
        boxes=tuple(boxes), spawn_position=(x, y + settings.PLAYER_EYE_HEIGHT, z),
        spawn_target=(x, y + settings.PLAYER_EYE_HEIGHT, z - 1), floor_colors=settings.FLOOR_COLORS,
        floor_material="concrete" if underground else layout.floor_materials[0],
        floor_heights=(-layout.basement.depth, 0.0, layout.floor_height) if underground else (0.0, layout.floor_height),
        goal_position=layout.goal_position, snow_enabled=False,
        lighting=lighting,
        decorations=tuple(decorations),
        base_height=-layout.basement.depth if underground else 0.0,
        floor_labels=("B1", "1", "2") if underground else (),
        floor_hints=("Lamp hall. Stairs lead back up.", "B1 stairs left of spawn. Exit upstairs.",
                     "Find the rusted exit frame.") if underground else (),
    )


def _build_lamp(light, ceiling, boxes, rotated=False):
    x, y, z = light.position
    casing = (0.52, 0.12, 1.12) if rotated else (1.12, 0.12, 0.52)
    panel = (0.32, 0.04, 0.92) if rotated else (0.92, 0.04, 0.32)
    boxes.append(Box((x, y + 0.17, z), casing, material="rust"))
    boxes.append(Box((x, y + 0.10, z), panel,
                     emission=tuple(channel * 1.8 for channel in light.color)))
    suspension = ceiling - (y + 0.23)
    if suspension > 0.05:
        boxes.append(Box((x, ceiling - suspension / 2, z), (0.04, suspension, 0.04), material="rust"))


def _build_stair_wing(layout: MazeLayout, link: StairLink, boxes: list[Box], points=None):
    _, bottom, top, _ = points or layout.stair_points(link)
    lower_y, upper_y = bottom[1], top[1]
    x, _, bottom_z = bottom
    top_z = top[2]
    direction = 1 if top_z > bottom_z else -1
    length = layout.stair_steps * layout.stair_run
    margin = (abs(top_z - bottom_z) - length) / 2
    start = bottom_z + direction * margin
    rise = (upper_y - lower_y) / layout.stair_steps
    wing_min, wing_max = min(bottom_z, top_z) - layout.cell_size / 2, max(bottom_z, top_z) + layout.cell_size / 2
    wing_depth = wing_max - wing_min
    roof = upper_y + layout.wall_height
    height = roof - lower_y
    wall = layout.wall_thickness
    rail = layout.rail_thickness

    for index in range(layout.stair_steps):
        step_y = (index + 1) * rise
        z = start + direction * (index + 0.5) * layout.stair_run
        boxes.append(Box((x, lower_y + step_y / 2, z), (layout.stair_width, step_y, layout.stair_run), material="concrete"))
        for side in (-1, 1):
            boxes.append(Box((x + side * (layout.stair_width + rail) / 2,
                              lower_y + (step_y + layout.rail_height) / 2, z),
                             (rail, step_y + layout.rail_height, layout.stair_run), material="rust"))

    front = start + direction * length
    back = top_z + direction * layout.cell_size / 2
    boxes.append(Box((x, upper_y - layout.slab_thickness / 2, (front + back) / 2),
                     (layout.wing_width, layout.slab_thickness, abs(back - front)), material="concrete"))
    # Ограда площадки оставляет проход ровно над лестничным маршем.
    guard_width = (layout.wing_width - layout.stair_width) / 2
    for side in (-1, 1):
        boxes.append(Box((x + side * (layout.stair_width + guard_width) / 2,
                          upper_y + layout.rail_height / 2, front),
                         (guard_width, layout.rail_height, rail), material="rust"))

    side = -1 if link.side == "west" else 1
    boxes.append(Box((x + side * (layout.wing_width - wall) / 2, lower_y + height / 2, (wing_min + wing_max) / 2),
                     (wall, height, wing_depth), material="concrete"))
    for z in (wing_min + wall / 2, wing_max - wall / 2):
        boxes.append(Box((x, lower_y + height / 2, z), (layout.wing_width, height, wall), material="concrete"))
    boxes.append(Box((x, roof + layout.slab_thickness / 2, (wing_min + wing_max) / 2),
                     (layout.wing_width, layout.slab_thickness, wing_depth), material="concrete"))
    if layout.basement is not None and lower_y == 0:
        boxes.append(Box((x, -layout.slab_thickness / 2, (wing_min + wing_max) / 2),
                         (layout.wing_width, layout.slab_thickness, wing_depth), material=layout.floor_materials[0]))
