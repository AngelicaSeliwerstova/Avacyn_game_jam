"""Navigation samples on supported floors and explicit, trusted stair links."""

import math
import glm

from engine.collision.world3d import CollisionWorld3D
from engine.navigation.graph import NavigationGraph


def build_hospital_navigation(level, stair, definitions, *, storey_definitions=None, floor_sizes=None):
    world = CollisionWorld3D((b.collider for b in level.collision_boxes + level.creator_objects),
                             level.floor_bounds, level.base_height)
    points, links, grid = [], [], {}
    storey_definitions = storey_definitions or (definitions,) * len(level.floor_heights)
    floor_sizes = floor_sizes or (level.floor_size,) * len(level.floor_heights)

    def add(point):
        points.append(tuple(point))
        return len(points) - 1

    def connect(a, b, terrain=False):
        links.append((a, b, terrain))

    def to_floor(index):
        p = points[index]
        for other, q in enumerate(points[:index]):
            if abs(p[1] - q[1]) < 0.001 and 0.01 < math.dist(p, q) <= 2.8:
                connect(index, other)

    for floor, height in enumerate(level.floor_heights):
        width, depth = floor_sizes[floor]
        for ix in range(math.ceil(width / 1.5)):
            for iz in range(math.ceil(depth / 1.5)):
                x, z = -width / 2 + ix * 1.5, -depth / 2 + iz * 1.5
                if math.hypot(x - stair.center[0], z - stair.center[1]) < 4.65:
                    continue
                p = glm.vec3(x, height, z)
                if world.is_blocked(p, 0.27, 1.8) or abs(world.support_height(p, 0.25, height) - height) > 0.02:
                    continue
                grid[floor, ix, iz] = add(p)
        for (f, ix, iz), index in tuple(grid.items()):
            if f != floor:
                continue
            for dx, dz in ((1, 0), (0, 1), (1, 1), (1, -1)):
                other = grid.get((floor, ix + dx, iz + dz))
                if other is not None:
                    connect(index, other)
        for data in storey_definitions[floor]:
            if data["type"] != "door":
                continue
            x, _, z = data["position"]
            axis = data.get("axis", "x")
            indices = []
            for side in (-0.65, 0, 0.65):
                index = add((x, height, z + side) if axis == "x" else (x + side, height, z))
                to_floor(index)
                indices.append(index)
            connect(indices[0], indices[1])
            connect(indices[1], indices[2])

    if len(level.floor_heights) > 1:
        radius = (stair.inner_radius + stair.outer_radius) / 2
        entry = add((stair.center[0], 0, stair.center[1] + 4.6))
        to_floor(entry)
        first = add(stair.point(89, radius))
        connect(entry, first)
        previous = first
        indices = []
        for p in stair.walking_path():
            index = add(p)
            connect(previous, index, True)
            previous = index
            indices.append(index)
        for floor in range(1, len(level.floor_heights)):
            height = level.floor_heights[floor]
            previous = indices[floor * stair.steps - 1]
            for x in (-12.2, -11, -9, -7):
                index = add((x, height, 6.9))
                connect(previous, index)
                previous = index
            to_floor(previous)
    return NavigationGraph(points, links, connection_distance=3.5)
