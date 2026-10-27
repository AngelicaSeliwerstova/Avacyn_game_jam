from dataclasses import dataclass
import heapq
import math


@dataclass(frozen=True)
class PathResult:
    points: tuple[tuple[float, float, float], ...]
    complete: bool


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
        for distance, i in candidates[:12]:
            if distance > self.connection_distance:
                break
            p = self.points[i]
            terrain = abs(p[1] - position[1]) > 1e-4
            if terrain and math.hypot(p[0] - position[0], p[2] - position[2]) > self.terrain_connection_distance:
                continue
            if traversal.can_walk(position, p, terrain, cache=False):
                result[i] = distance
        return result

    def find_path(self, start, goal, traversal) -> PathResult:
        start, goal = tuple(start), tuple(goal)
        if any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in (start, goal)):
            raise ValueError("Path endpoints need three finite coordinates")
        starts, ends = self._connections(start, traversal), self._connections(goal, traversal)
        if not starts:
            return PathResult((), False)
        costs = dict(starts)
        previous = {i: None for i in starts}
        heap = [(cost + math.dist(self.points[i], goal), cost, i) for i, cost in starts.items()]
        heapq.heapify(heap)
        visited = set()
        best = min(starts, key=lambda i: math.dist(self.points[i], goal))
        complete = False
        while heap:
            _, cost, current = heapq.heappop(heap)
            if current in visited:
                continue
            visited.add(current)
            if math.dist(self.points[current], goal) < math.dist(self.points[best], goal):
                best = current
            if current in ends:
                best, complete = current, True
                break
            for neighbor, terrain in self.links[current]:
                if neighbor in visited:
                    continue
                a, b = self.points[current], self.points[neighbor]
                candidate = cost + math.dist(a, b)
                if candidate >= costs.get(neighbor, math.inf) or not traversal.can_walk(a, b, terrain):
                    continue
                costs[neighbor], previous[neighbor] = candidate, current
                heapq.heappush(heap, (candidate + math.dist(b, goal), candidate, neighbor))
        route = []
        current = best
        while current is not None:
            route.append(self.points[current])
            current = previous[current]
        route.reverse()
        if complete:
            route.append(goal)
        filtered = []
        last = start
        for p in route:
            if math.dist(p, last) > 0.05:
                filtered.append(p)
                last = p
        return PathResult(tuple(filtered), complete)
