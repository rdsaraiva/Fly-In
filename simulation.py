"""Turn-by-turn execution and validation of the drone plans."""

from models import Graph
from pathfinding import Reservations


class SimulationError(Exception):
    """Raised when the plans break a movement or capacity rule."""


class Simulation:
    """Replay the plans, check every rule and produce the output lines."""

    def __init__(self, graph: Graph, paths: list[list[str]]) -> None:
        """Store the graph and the plan of each drone."""
        self.graph = graph
        self.paths = paths

    @property
    def total_turns(self) -> int:
        """Return the turn in which the last drone is delivered."""
        return max(len(path) - 1 for path in self.paths)

    def validate(self) -> None:
        """Raise SimulationError if any zone or link is over capacity."""
        table = Reservations(self.graph)
        for path in self.paths:
            table.reserve(path)
        for (zone, turn), count in table.zones.items():
            if (
                zone not in (self.graph.start, self.graph.end)
                and count > self.graph.zones[zone].max_drones
            ):
                raise SimulationError(
                    f"turn {turn}: zone '{zone}' over capacity"
                )
        for (key, turn), count in table.links.items():
            if count > self.graph.connections[key].max_link_capacity:
                link = "-".join(sorted(key))
                raise SimulationError(
                    f"turn {turn}: link '{link}' over capacity"
                )

    def moves_at(self, turn: int) -> list[str]:
        """Return the 'D<id>-<position>' moves made during `turn`."""
        return [
            f"D{n}-{path[turn]}"
            for n, path in enumerate(self.paths, start=1)
            if turn < len(path) and path[turn] != path[turn - 1]
        ]

    def run(self) -> list[str]:
        """Validate the plans and return one output line per turn."""
        self.validate()
        return [
            " ".join(self.moves_at(t))
            for t in range(1, self.total_turns + 1)
        ]

    def metrics(self) -> str:
        """Return a one-line summary: turns, average and total moves."""
        average = sum(len(path) - 1 for path in self.paths) / len(self.paths)
        moves = sum(
            len(self.moves_at(t)) for t in range(1, self.total_turns + 1)
        )
        return (
            f"Turns: {self.total_turns} | Avg turns/drone: {average:.1f}"
            f" | Total moves: {moves}"
        )
