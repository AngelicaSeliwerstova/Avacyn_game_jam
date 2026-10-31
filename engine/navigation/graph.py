from dataclasses import dataclass
import heapq
import math
from time import perf_counter


@dataclass(frozen=True)
class PathResult:
    points: tuple[tuple[float, float, float], ...]
    complete: bool


class PathSearch:
    def __init__(self, graph, start, goal, traversal):
        self._graph = graph
        self._start = start
        self._goal = goal
        self._traversal = traversal
        starts = graph._connections(start, traversal)
        self._ends = graph._connections(goal, traversal)
        self._costs = dict(starts)
        self._previous = {index: None for index in starts}
        self._heap = [
            (cost + math.dist(graph.points[index], goal), cost, index)
            for index, cost in starts.items()
        ]
        heapq.heapify(self._heap)
        self._visited = set()
        self._best = min(
            starts, key=lambda index: math.dist(graph.points[index], goal),
            default=None,
        )
        self._complete = False
        self.result = None
        if not starts:
            self._finish()

    @property
    def done(self):
        return self.result is not None

    def advance(self, max_expansions=32, max_seconds=0.002):
        if (max_expansions <= 0 or not math.isfinite(max_seconds)
                or max_seconds <= 0):
            raise ValueError("Path search budgets must be positive")
        deadline = perf_counter() + max_seconds
        expanded = 0
        while self._heap and expanded < max_expansions and perf_counter() < deadline:
            _, cost, current = heapq.heappop(self._heap)
            if current in self._visited:
                continue
            self._visited.add(current)
            expanded += 1
            if math.dist(self._graph.points[current], self._goal) < math.dist(
                self._graph.points[self._best], self._goal,
            ):
                self._best = current
            if current in self._ends:
                self._best, self._complete = current, True
                self._finish()
                return expanded
            for neighbor, terrain in self._graph.links[current]:
                if neighbor in self._visited:
                    continue
                a, b = self._graph.points[current], self._graph.points[neighbor]
                candidate = cost + math.dist(a, b)
                if candidate >= self._costs.get(neighbor, math.inf) or not self._traversal.can_walk(
                    a, b, terrain,
                ):
                    continue
                self._costs[neighbor], self._previous[neighbor] = candidate, current
                heapq.heappush(
                    self._heap,
                    (candidate + math.dist(b, self._goal), candidate, neighbor),
                )
        if not self._heap:
            self._finish()
        return expanded

    def _finish(self):
        route = []
        current = self._best
        while current is not None:
            route.append(self._graph.points[current])
            current = self._previous[current]
        route.reverse()
        if self._complete:
            route.append(self._goal)
        filtered = []
        last = self._start
        for point in route:
            if math.dist(point, last) > 0.05:
                filtered.append(point)
                last = point
        self.result = PathResult(tuple(filtered), self._complete)


class NavigationGraph:
    """A* по точкам сцены. terrain-связи описывают подготовленные лестницы и склоны."""

    def __init__(self, points, links, connection_distance=4.5, terrain_connection_distance=1.0):
        if not all(math.isfinite(v) and v > 0 for v in (connection_distance, terrain_connection_distance)):
            raise ValueError("Navigation connection distances must be positive and finite")
        self.connection_distance = connection_distance
        self.terrain_connection_distance = terrain_connection_distance
        self.points = tuple(tuple(p) for p in points)
        if any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in self.points):
            raise ValueError("Navigation points need three finite coordinates")
        adjacency = [[] for _ in self.points]
        for a, b, terrain in links:
            if not 0 <= a < len(self.points) or not 0 <= b < len(self.points) or a == b:
                raise ValueError("Navigation links must reference two different points")
            adjacency[a].append((b, terrain))
            adjacency[b].append((a, terrain))
        self.links = tuple(tuple(edges) for edges in adjacency)

    def _connections(self, position, traversal):
        candidates = sorted((math.dist(position, p), i) for i, p in enumerate(self.points)
                            if abs(p[1] - position[1]) <= traversal.step_height + 1e-4)
        result = {}
        for distance, i in candidates:
            if distance > self.connection_distance:
                break
            p = self.points[i]
            terrain = abs(p[1] - position[1]) > 1e-4
            if terrain and math.hypot(p[0] - position[0], p[2] - position[2]) > self.terrain_connection_distance:
                continue
            if traversal.can_walk(position, p, terrain, cache=False):
                result[i] = distance
                if len(result) == 12:
                    break
        return result

    def start_path_search(self, start, goal, traversal) -> PathSearch:
        start, goal = tuple(start), tuple(goal)
        if any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in (start, goal)):
            raise ValueError("Path endpoints need three finite coordinates")
        return PathSearch(self, start, goal, traversal)

    def find_path(self, start, goal, traversal) -> PathResult:
        search = self.start_path_search(start, goal, traversal)
        while not search.done:
            search.advance(max_expansions=max(1, len(self.points)), max_seconds=3600)
        return search.result
