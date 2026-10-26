from collections import deque
from dataclasses import dataclass
import json
import math
from pathlib import Path


Node = tuple[int, int, int]  # Этаж, строка, столбец.
Point = tuple[float, float, float]


@dataclass(frozen=True)
class StairLink:
    name: str
    side: str
    lower_row: int
    upper_row: int


@dataclass(frozen=True)
class MazeLayout:
    floors: tuple[tuple[str, ...], ...]
    cell_size: float
    floor_height: float
    wall_height: float
    slab_thickness: float
    wing_width: float
    wall_thickness: float
    stair_steps: int
    stair_run: float
    stair_width: float
    rail_height: float
    rail_thickness: float
    balcony_depth: float
    floor_materials: tuple[str, ...]
    wall_materials: tuple[tuple[str, ...], ...]
    stairs: tuple[StairLink, ...]
    spawn: Node
    exit: Node

    def __post_init__(self):
        if len(self.floors) != 2 or len(self.floor_materials) != 2 or len(self.wall_materials) != 2:
            raise ValueError("Maze needs two floors and their materials")
        if any(not floor or not floor[0] for floor in self.floors) or any(not names for names in self.wall_materials):
            raise ValueError("Maze grids and wall material lists must not be empty")
        width, depth = len(self.floors[0][0]), len(self.floors[0])
        if min(width, depth) < 7 or any(
            len(floor) != depth or any(len(row) != width or set(row) - {"#", "."} for row in floor)
            for floor in self.floors
        ):
            raise ValueError("Maze floors must be equally sized rectangular grids of # and .")
        values = (self.cell_size, self.floor_height, self.wall_height, self.slab_thickness,
                  self.wing_width, self.wall_thickness, self.stair_run, self.stair_width,
                  self.rail_height, self.rail_thickness, self.balcony_depth)
        if (any(not math.isfinite(value) or value <= 0 for value in values)
                or not isinstance(self.stair_steps, int) or self.stair_steps < 1):
            raise ValueError("Maze dimensions must be finite and positive")
        if abs(self.wall_height + self.slab_thickness - self.floor_height) > 1e-6:
            raise ValueError("Walls and ceiling slab must fill the floor height")
        if self.stair_width + 2 * self.rail_thickness >= self.wing_width:
            raise ValueError("Stair flight must fit inside its wing")
        for link in self.stairs:
            if link.side not in ("west", "east"):
                raise ValueError("Stair wing must be west or east")
            if abs(link.upper_row - link.lower_row) * self.cell_size <= self.stair_steps * self.stair_run:
                raise ValueError("Stair flight needs landings at both ends")
            if not all(self.is_open(node) for node in self.stair_nodes(link)):
                raise ValueError("Stair doors must be open in both grids")
        if not self.is_open(self.spawn) or not self.is_open(self.exit):
            raise ValueError("Maze spawn and exit must be open")
        if self.exit[0] != 1 or self.exit[1] != 0:
            raise ValueError("Maze exit must lead north from the upper floor")

    @property
    def width(self) -> float:
        return len(self.floors[0][0]) * self.cell_size

    @property
    def depth(self) -> float:
        return len(self.floors[0]) * self.cell_size

    def is_open(self, node: Node) -> bool:
        floor, row, column = node
        return (0 <= floor < len(self.floors) and 0 <= row < len(self.floors[floor])
                and 0 <= column < len(self.floors[floor][row]) and self.floors[floor][row][column] == ".")

    def position(self, node: Node) -> Point:
        floor, row, column = node
        return ((column + 0.5) * self.cell_size - self.width / 2,
                floor * self.floor_height, (row + 0.5) * self.cell_size - self.depth / 2)

    def stair_nodes(self, link: StairLink) -> tuple[Node, Node]:
        column = 0 if link.side == "west" else len(self.floors[0][0]) - 1
        return (0, link.lower_row, column), (1, link.upper_row, column)

    def stair_points(self, link: StairLink) -> tuple[Point, ...]:
        lower, upper = map(self.position, self.stair_nodes(link))
        side = -1 if link.side == "west" else 1
        x = side * (self.width + self.wing_width) / 2
        return (lower, (x, 0.0, lower[2]), (x, self.floor_height, upper[2]), upper)

    @property
    def goal_position(self) -> Point:
        x, y, _ = self.position(self.exit)
        return x, y, -self.depth / 2 - self.balcony_depth / 2

    def neighbors(self, node: Node):
        floor, row, column = node
        for dr, dc in ((-1, 0), (0, 1), (1, 0), (0, -1)):
            neighbor = floor, row + dr, column + dc
            if self.is_open(neighbor):
                yield neighbor
        for link in self.stairs:
            lower, upper = self.stair_nodes(link)
            if node == lower:
                yield upper
            elif node == upper:
                yield lower

    def path(self, start: Node, goal: Node) -> tuple[Node, ...]:
        previous = {start: None}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            if node == goal:
                route = []
                while node is not None:
                    route.append(node)
                    node = previous[node]
                return tuple(reversed(route))
            for neighbor in self.neighbors(node):
                if neighbor not in previous:
                    previous[neighbor] = node
                    queue.append(neighbor)
        raise ValueError(f"No maze route from {start} to {goal}")

    def walk_points(self, route: tuple[Node, ...]) -> tuple[Point, ...]:
        """Разворачивает переход между этажами в реальный путь через лестницу."""
        points = [self.position(route[0])]
        for previous, node in zip(route, route[1:]):
            if previous[0] != node[0]:
                for link in self.stairs:
                    lower, upper = self.stair_nodes(link)
                    if {previous, node} == {lower, upper}:
                        stairs = self.stair_points(link)
                        points.extend(stairs[1:] if previous == lower else tuple(reversed(stairs))[1:])
                        break
                else:
                    raise ValueError("Floor transition has no staircase")
            else:
                points.append(self.position(node))
        return tuple(points)


def load_maze_layout(path: Path) -> MazeLayout:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["floors"] = tuple(tuple(rows) for rows in data["floors"])
    data["stairs"] = tuple(StairLink(**link) for link in data["stairs"])
    data["spawn"] = tuple(data["spawn"])
    data["exit"] = tuple(data["exit"])
    data["floor_materials"] = tuple(data["floor_materials"])
    data["wall_materials"] = tuple(tuple(names) for names in data["wall_materials"])
    return MazeLayout(**data)
