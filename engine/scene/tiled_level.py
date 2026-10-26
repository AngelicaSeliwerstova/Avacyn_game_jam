import math
from pathlib import Path

import pytmx

from engine.scene.box import Box
from engine.scene.level import Level


def load_tiled_level(
    path: Path,
    eye_height: float,
    floor_colors: tuple[tuple[int, int, int], tuple[int, int, int]],
) -> Level:
    """Загружает конечную ортогональную TMX-карту: стены и точку старта."""
    tiled = pytmx.TiledMap(str(path))
    if tiled.orientation != "orthogonal" or int(getattr(tiled, "infinite", 0)):
        raise ValueError("Only finite orthogonal Tiled maps are supported")
    if min(tiled.width, tiled.height, tiled.tilewidth, tiled.tileheight) <= 0:
        raise ValueError("Tiled map dimensions must be positive")

    cell_size = float(tiled.properties["cell_size"])
    wall_height = float(tiled.properties["wall_height"])
    floor_tile_size = float(tiled.properties["floor_tile_size"])
    if any(not math.isfinite(value) or value <= 0 for value in (
        cell_size, wall_height, floor_tile_size, eye_height,
    )):
        raise ValueError("Map sizes and player height must be positive finite numbers")

    walls = tiled.get_layer_by_name("walls")
    spawns = tiled.get_layer_by_name("spawn")
    if not isinstance(walls, pytmx.TiledTileLayer) or not isinstance(spawns, pytmx.TiledObjectGroup):
        raise ValueError("Map needs a walls tile layer and a spawn object layer")
    if walls.width != tiled.width or walls.height != tiled.height:
        raise ValueError("Walls layer must cover the entire map")

    width, depth = tiled.width * cell_size, tiled.height * cell_size
    boxes = []
    for row, cells in enumerate(walls.data):
        for column, gid in enumerate(cells):
            if gid:
                boxes.append(Box(
                    position=(
                        (column + 0.5) * cell_size - width / 2,
                        wall_height / 2,
                        (row + 0.5) * cell_size - depth / 2,
                    ),
                    size=(cell_size, wall_height, cell_size),
                ))

    players = [obj for obj in spawns if obj.name == "player"]
    if len(players) != 1:
        raise ValueError("Map must contain exactly one spawn object named player")
    player = players[0]
    yaw_degrees = float(player.properties["yaw_degrees"])
    if not all(math.isfinite(value) for value in (player.x, player.y, yaw_degrees)):
        raise ValueError("Spawn coordinates and yaw must be finite")
    if not (0 <= player.x < tiled.width * tiled.tilewidth and 0 <= player.y < tiled.height * tiled.tileheight):
        raise ValueError("Player spawn lies outside the map")
    column = int(player.x / tiled.tilewidth)
    row = int(player.y / tiled.tileheight)
    if walls.data[row][column]:
        raise ValueError("Player spawn lies inside a wall tile")

    x = player.x / tiled.tilewidth * cell_size - width / 2
    z = player.y / tiled.tileheight * cell_size - depth / 2
    yaw = math.radians(yaw_degrees)
    return Level(
        floor_size=(width, depth),
        floor_tile_size=floor_tile_size,
        boxes=tuple(boxes),
        spawn_position=(x, eye_height, z),
        spawn_target=(x + math.cos(yaw), eye_height, z + math.sin(yaw)),
        floor_colors=floor_colors,
    )
