import math
from dataclasses import replace
from pathlib import Path

from config import settings
from engine.scene.box import Box
from engine.scene.camera import FixedCameraZone
from engine.scene.level import Level
from engine.scene.lighting import Lighting, PointLight
from game.levels.basement import build_basement_room
from game.levels.cameras import camera_layout_path, load_fixed_cameras
from game.levels.creator import creator_objects_path, load_creator_objects
from game.levels.crawl import build_crawl_passage
from game.levels.navigation import build_maze_navigation
from game.levels.maze_layout import MazeLayout, StairLink, load_maze_layout


def maze_layout_path() -> Path:
    return Path(__file__).resolve().parents[2] / "resources" / "levels" / settings.MAZE_LAYOUT


def create_maze_level() -> Level:
    layout = load_maze_layout(maze_layout_path())
    authored_cameras = load_fixed_cameras(camera_layout_path())
    automatic_cameras = _build_fixed_cameras(layout)
    creator_objects = load_creator_objects(creator_objects_path())
    boxes = []
    cell = layout.cell_size
    thickness = layout.slab_thickness
    roof_y = layout.floor_height + layout.wall_height
    passages = {passage.node: passage for passage in layout.crawl_passages}

    for floor, rows in enumerate(layout.floors):
        base = floor * layout.floor_height
        materials = layout.wall_materials[floor]
        for row, cells in enumerate(rows):
            start = 0
            while start < len(cells):
                if cells[start] != "#":
                    start += 1
                    continue
                material = materials[min(len(materials) - 1, row * len(materials) // len(rows))]
                if (floor, row, start) in passages:
                    build_crawl_passage(layout, passages[floor, row, start], boxes, material)
                    start += 1
                    continue
                end = start + 1
                while end < len(cells) and cells[end] == "#" and (floor, row, end) not in passages:
                    end += 1
                # Соседние стеновые клетки объединяются в один блок.
                boxes.append(Box(
                    ((start + end) * cell / 2 - layout.width / 2,
                     base + layout.wall_height / 2, (row + 0.5) * cell - layout.depth / 2),
                    ((end - start) * cell, layout.wall_height, cell),
                    material=material,
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

    x, y, z = layout.position(layout.spawn)
    decorations = []
    lighting = layout.lighting
    if layout.lighting is not None:
        for index, light in enumerate(layout.lighting.lights):
            ceiling = roof_y if abs(light.position[0]) > layout.width / 2 else (
                layout.wall_height + (layout.floor_height if light.position[1] > layout.floor_height else 0)
            )
            _build_lamp(light, ceiling, decorations, light_index=index)
        if layout.basement is not None:
            lights = layout.basement.lights(layout)
            for index, light in enumerate(lights):
                _build_lamp(light, -thickness, decorations, rotated=bool(index % 2),
                            light_index=len(layout.lighting.lights) + index)
            extra = []
            for point in layout.basement.stair_points(layout)[1:3]:
                px, py, pz = point
                light = PointLight((px, py + layout.wall_height - 0.24, pz), (1.0, 0.65, 0.35), 2.6, 6.0)
                _build_lamp(light, layout.wall_height, decorations,
                            light_index=len(layout.lighting.lights) + len(lights) + len(extra))
                extra.append(light)
            lighting = Lighting(lighting.ambient, lighting.lights + lights + tuple(extra), lighting.shadow_resolution)
        lighting, decorations = _power_lamps(lighting, decorations, layout.lamp_power_pattern)
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
        decorations=tuple(decorations) + creator_objects,
        objects=layout.objects,
        navigation=build_maze_navigation(layout),
        base_height=-layout.basement.depth if underground else 0.0,
        floor_labels=("B1", "1", "2") if underground else (),
        floor_hints=("Lamp hall. Stairs lead back up.", "The staircases need the upper-floor key.",
                     "The balcony door needs its own key.") if underground else (),
        fixed_cameras=(authored_cameras or ()) + automatic_cameras,
        camera_save_path=camera_layout_path(),
        fixed_cameras_authored=authored_cameras is not None,
        authored_fixed_cameras=authored_cameras or (),
        creator_objects=creator_objects,
        creator_objects_path=creator_objects_path(),
    )


def _build_fixed_cameras(layout: MazeLayout) -> tuple[FixedCameraZone, ...]:
    cameras = []
    stair_nodes = {node for link in layout.stairs for node in layout.stair_nodes(link)}
    if layout.basement is not None:
        stair_nodes.add(layout.basement.entry)

    for floor, rows in enumerate(layout.floors):
        for row, cells in enumerate(rows):
            for column, cell in enumerate(cells):
                node = floor, row, column
                if cell != "." or node in stair_nodes or node == layout.exit:
                    continue
                camera_node = next(
                    (neighbor for neighbor in layout.neighbors(node) if neighbor[0] == floor),
                    None,
                )
                if camera_node is None:
                    continue

                x, y, z = layout.position(node)
                camera_x, _, camera_z = layout.position(camera_node)
                half_cell = layout.cell_size / 2
                cameras.append(FixedCameraZone(
                    minimum=(x - half_cell, y - 0.15, z - half_cell),
                    maximum=(x + half_cell, y + layout.floor_height * 0.75, z + half_cell),
                    position=(camera_x, y + 2.35, camera_z),
                    target=(x, y + 1.0, z),
                ))

    if layout.basement is not None:
        spec = layout.basement
        bottom, ceiling = -spec.depth, -layout.slab_thickness
        columns = math.ceil(layout.width / layout.cell_size)
        rows = math.ceil(layout.depth / layout.cell_size)
        sector_width, sector_depth = layout.width / columns, layout.depth / rows
        for row in range(rows):
            for column in range(columns):
                x = -layout.width / 2 + (column + 0.5) * sector_width
                z = -layout.depth / 2 + (row + 0.5) * sector_depth
                camera_position = (x + sector_width * 0.12, ceiling - 0.25, z + sector_depth * 0.12)
                cameras.append(FixedCameraZone(
                    minimum=(-layout.width / 2 + column * sector_width, bottom - 0.1,
                             -layout.depth / 2 + row * sector_depth),
                    maximum=(-layout.width / 2 + (column + 1) * sector_width, ceiling,
                             -layout.depth / 2 + (row + 1) * sector_depth),
                    position=camera_position,
                    target=(x, bottom + 1.0, z),
                ))
    return tuple(cameras)


def _power_lamps(lighting, decorations, pattern):
    """Сохраняет корпуса погасших ламп, оставляя на GPU только работающие источники."""
    active, indices = [], {}
    for index, light in enumerate(lighting.lights):
        if pattern[index % len(pattern)]:
            indices[index] = len(active)
            active.append(light)
    panels = []
    for box in decorations:
        if box.emission_light is not None:
            old_index = box.emission_light
            box = replace(box, emission_light=indices.get(old_index),
                          emission=box.emission if old_index in indices else (0, 0, 0))
        panels.append(box)
    return replace(lighting, lights=tuple(active)), panels


def _build_lamp(light, ceiling, boxes, rotated=False, light_index=None):
    x, y, z = light.position
    casing = (0.52, 0.12, 1.12) if rotated else (1.12, 0.12, 0.52)
    panel = (0.32, 0.04, 0.92) if rotated else (0.92, 0.04, 0.32)
    boxes.append(Box((x, y + 0.17, z), casing, material="rust"))
    boxes.append(Box((x, y + 0.10, z), panel,
                     emission=tuple(channel * 1.8 for channel in light.color), emission_light=light_index))
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
