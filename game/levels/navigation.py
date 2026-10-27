from engine.navigation.graph import NavigationGraph


def build_maze_navigation(layout):
    """Сеть проходов той же разметки, из которой собирается геометрия уровня."""
    points, indices, links = [], {}, set()

    def node(position):
        position = tuple(round(v, 6) for v in position)
        if position not in indices:
            indices[position] = len(points)
            points.append(position)
        return indices[position]

    def connect(a, b, terrain=False):
        a, b = node(a), node(b)
        if a != b:
            links.add((min(a, b), max(a, b), terrain))

    for floor, rows in enumerate(layout.floors):
        for row, line in enumerate(rows):
            for column, cell in enumerate(line):
                if cell != ".":
                    continue
                here = (floor, row, column)
                node(layout.position(here))
                for dr, dc in ((0, 1), (1, 0)):
                    other = floor, row + dr, column + dc
                    if layout.is_open(other):
                        connect(layout.position(here), layout.position(other))

    for passage in layout.crawl_passages:
        a, b = passage.endpoints
        center = layout.position(passage.node)
        connect(layout.position(a), center)
        connect(center, layout.position(b))

    def stairs(path):
        entrance, bottom, top, exit = path
        connect(entrance, bottom)
        direction = 1 if top[2] > bottom[2] else -1
        run = layout.stair_steps * layout.stair_run
        margin = (abs(top[2] - bottom[2]) - run) / 2
        start = bottom[2] + direction * margin
        previous = bottom
        for step in range(layout.stair_steps):
            tread = (bottom[0], bottom[1] + (top[1] - bottom[1]) * (step + 1) / layout.stair_steps,
                     start + direction * (step + 0.5) * layout.stair_run)
            connect(previous, tread, terrain=True)
            previous = tread
        connect(previous, top, terrain=True)
        connect(top, exit)

    for link in layout.stairs:
        stairs(layout.stair_points(link))
    if layout.basement is not None:
        y = -layout.basement.depth
        for row in range(len(layout.floors[0])):
            for column in range(len(layout.floors[0][0])):
                x, _, z = layout.position((0, row, column))
                point = (x, y, z)
                node(point)
                if column > 0:
                    connect((x - layout.cell_size, y, z), point)
                if row > 0:
                    connect((x, y, z - layout.cell_size), point)
        stairs(layout.basement.stair_points(layout))
    connect(layout.position(layout.exit), layout.goal_position)
    return NavigationGraph(points, sorted(links), connection_distance=layout.cell_size * 1.5,
                           terrain_connection_distance=layout.stair_run * 2)
