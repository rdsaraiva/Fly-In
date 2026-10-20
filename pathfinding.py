"""Time-expanded Dijkstra planner for the drone fleet."""

import heapq
from collections import Counter
from collections.abc import Iterator

from models import Connection, ConnectionKey, Graph, ZoneType

State = tuple[str, int]


class PathError(Exception):
    """Raised when no drone can reach the end zone."""


class Reservations:
    """Count how many drones use each zone and link at each turn."""

    def __init__(self, graph: Graph) -> None:
        """Start with an empty table for the given graph."""
        self.graph = graph
        self.zones: Counter[State] = Counter()
        self.links: Counter[tuple[ConnectionKey, int]] = Counter()

    def zone_free(self, name: str, turn: int) -> bool:
        """Return True if one more drone fits in `name` at `turn`."""
        return (
            name in (self.graph.start, self.graph.end)
            or self.zones[(name, turn)] < self.graph.zones[name].max_drones
        )

    def link_free(self, a: str, b: str, turn: int) -> bool:
        """Return True if one more drone fits on link a-b at `turn`."""
        key = Connection.key(a, b)
        return (
            self.links[(key, turn)]
            < self.graph.connections[key].max_link_capacity
        )

    def reserve(self, path: list[str]) -> None:
        """Book every zone and link used by `path` (one entry per turn)."""
        for t in range(1, len(path)):
            prev, cur = path[t - 1], path[t]
            if "-" not in cur:
                self.zones[(cur, t)] += 1
            if prev != cur:
                if "-" in cur:
                    link = cur
                elif "-" in prev:
                    link = prev
                else:
                    link = f"{prev}-{cur}"
                self.links[(Connection.key(*link.split("-")), t)] += 1


class PathFinder:
    """Plan drones one by one, each avoiding the earlier reservations."""

    def __init__(self, graph: Graph, nb_drones: int) -> None:
        """Store the graph and an empty reservation table."""
        self.graph = graph
        self.nb_drones = nb_drones
        self.reservations = Reservations(graph)

    def plan_all(self) -> list[list[str]]:
        """Return one path per drone; path[t] is its position at turn t."""
        paths: list[list[str]] = []
        for _ in range(self.nb_drones):
            last = max((len(p) - 1 for p in paths), default=0)
            limit = last + 2 * len(self.graph.zones)
            path = self.find_path(limit)
            if path is None:
                raise PathError("no path from start to end")
            self.reservations.reserve(path)
            paths.append(path)
        return paths

    def moves(self, zone: str, turn: int) -> Iterator[State]:
        """Yield every (zone, arrival turn) reachable from `zone`."""
        res = self.reservations
        if res.zone_free(zone, turn + 1):
            yield zone, turn + 1
        for nb in self.graph.get_neighbors(zone):
            target = self.graph.zones[nb]
            if target.zone_type is ZoneType.BLOCKED:
                continue
            arrive = turn + target.move_cost
            if res.zone_free(nb, arrive) and all(
                res.link_free(zone, nb, t) for t in range(turn + 1, arrive + 1)
            ):
                yield nb, arrive

    def find_path(self, limit: int) -> list[str] | None:
        """Return the earliest-arrival path, or None within `limit`."""
        heap: list[tuple[int, int, str, State | None]] = [
            (0, 0, self.graph.start, None)
        ]
        parent: dict[State, State | None] = {}
        while heap:
            turn, score, zone, prev = heapq.heappop(heap)
            state = (zone, turn)
            if state in parent:
                continue
            parent[state] = prev
            if zone == self.graph.end:
                return self.build_path(parent, state)
            if turn >= limit:
                continue
            for nxt, arrive in self.moves(zone, turn):
                bonus = (
                    nxt != zone
                    and self.graph.zones[nxt].zone_type is ZoneType.PRIORITY
                )
                heapq.heappush(heap, (arrive, score - bonus, nxt, state))
        return None

    @staticmethod
    def build_path(
        parent: dict[State, State | None], state: State | None
    ) -> list[str]:
        """Walk the parents back to the start, adding in-flight steps."""
        path: list[str] = []
        while state is not None:
            zone, turn = state
            path.append(zone)
            prev_state = parent[state]
            if prev_state is not None:
                prev_zone, prev_turn = prev_state
                if turn - prev_turn == 2:
                    path.append(f"{prev_zone}-{zone}")
            state = prev_state
        return path[::-1]
