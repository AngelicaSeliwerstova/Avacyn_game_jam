from pathlib import Path

from config import settings
from engine.scene.box import Box
from engine.scene.level import Level
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
    return Level(
        floor_size=(layout.width + 2 * layout.wing_width, layout.depth + 2 * layout.balcony_depth),
        floor_tile_size=settings.FLOOR_TILE_SIZE,
        boxes=tuple(boxes), spawn_position=(x, y + settings.PLAYER_EYE_HEIGHT, z),
        spawn_target=(x, y + settings.PLAYER_EYE_HEIGHT, z - 1), floor_colors=settings.FLOOR_COLORS,
        floor_material=layout.floor_materials[0], floor_heights=(0.0, layout.floor_height),
        goal_position=layout.goal_position, snow_enabled=False,
    )


def _build_stair_wing(layout: MazeLayout, link: StairLink, boxes: list[Box]):
    _, bottom, top, _ = layout.stair_points(link)
    x, _, bottom_z = bottom
    top_z = top[2]
    direction = 1 if top_z > bottom_z else -1
    length = layout.stair_steps * layout.stair_run
    margin = (abs(top_z - bottom_z) - length) / 2
    start = bottom_z + direction * margin
    rise = layout.floor_height / layout.stair_steps
    wing_min, wing_max = min(bottom_z, top_z) - layout.cell_size / 2, max(bottom_z, top_z) + layout.cell_size / 2
    wing_depth = wing_max - wing_min
    height = layout.floor_height + layout.wall_height
    wall = layout.wall_thickness
    rail = layout.rail_thickness

    for index in range(layout.stair_steps):
        step_y = (index + 1) * rise
        z = start + direction * (index + 0.5) * layout.stair_run
        boxes.append(Box((x, step_y / 2, z), (layout.stair_width, step_y, layout.stair_run), material="concrete"))
        for side in (-1, 1):
            boxes.append(Box((x + side * (layout.stair_width + rail) / 2,
                              (step_y + layout.rail_height) / 2, z),
                             (rail, step_y + layout.rail_height, layout.stair_run), material="rust"))

    front = start + direction * length
    back = top_z + direction * layout.cell_size / 2
    boxes.append(Box((x, layout.floor_height - layout.slab_thickness / 2, (front + back) / 2),
                     (layout.wing_width, layout.slab_thickness, abs(back - front)), material="concrete"))
    # Ограда площадки оставляет проход ровно над лестничным маршем.
    guard_width = (layout.wing_width - layout.stair_width) / 2
    for side in (-1, 1):
        boxes.append(Box((x + side * (layout.stair_width + guard_width) / 2,
                          layout.floor_height + layout.rail_height / 2, front),
                         (guard_width, layout.rail_height, rail), material="rust"))

    side = -1 if link.side == "west" else 1
    boxes.append(Box((x + side * (layout.wing_width - wall) / 2, height / 2, (wing_min + wing_max) / 2),
                     (wall, height, wing_depth), material="concrete"))
    for z in (wing_min + wall / 2, wing_max - wall / 2):
        boxes.append(Box((x, height / 2, z), (layout.wing_width, height, wall), material="concrete"))
    boxes.append(Box((x, height + layout.slab_thickness / 2, (wing_min + wing_max) / 2),
                     (layout.wing_width, layout.slab_thickness, wing_depth), material="concrete"))
