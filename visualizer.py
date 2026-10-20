"""Colored terminal view of the simulation."""

from collections import Counter

from models import ZoneType
from simulation import Simulation


class Visualizer:
    """Show every turn with ANSI colors and the occupancy of each zone."""

    COLORS = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "gray": "\033[90m",
        "black": "\033[30m",
        "orange": "\033[38;5;208m",
        "bright": "\033[1;97m",
    }
    RESET = "\033[0m"

    def __init__(self, simulation: Simulation) -> None:
        """Keep the simulation and the names of the table columns."""
        self.simulation = simulation
        self.graph = simulation.graph

        self.names: list[str] = []
        for name, zone in self.graph.zones.items():
            if zone.zone_type is ZoneType.BLOCKED:
                continue
            self.names.append(name)

    def width(self, name: str) -> int:
        """Return the column width of the zone name."""
        m = self.graph.zones[name].max_drones
        return max(len(name), len(f"{m}/{m}"))

    def paint(self, text: str, color: str | None) -> str:
        """Wrap `text` in the ANSI code of `color`; unknown stay plain."""
        code = self.COLORS.get(color or "")
        return f"{code}{text}{self.RESET}" if code else text

    def occupancy(self, turn: int) -> Counter[str]:
        """Return how many drones are in each zone at the end of `turn`."""
        return Counter(
            zone
            for path in self.simulation.paths
            if "-" not in (zone := path[min(turn, len(path) - 1)])
        )

    def header(self) -> str:
        """Return the 'Turn | <zones> | Moves' line."""
        cols: list[str] = []
        for name in self.names:
            aligned = f"{name:>{self.width(name)}}"
            cols.append(self.paint(aligned, self.graph.zones[name].color))
        return f"Turn | {' | '.join(cols)} | Moves"

    def cell(self, name: str, count: int) -> str:
        """Return 'count/max' in its column, red when the zone is full."""
        zone = self.graph.zones[name]
        text = f"{count}/{zone.max_drones}"
        aligned = f"{text:>{self.width(name)}}"
        if count >= zone.max_drones:
            return self.paint(aligned, "red")
        return aligned

    def render_turn(self, turn: int) -> str:
        """Return the colored moves of `turn` and the state of every zone."""
        moves = []
        for move in self.simulation.moves_at(turn):
            target = move.rsplit("-", 1)[1]
            moves.append(self.paint(move, self.graph.zones[target].color))
        counts = self.occupancy(turn)
        cells = [self.cell(name, counts[name]) for name in self.names]
        return f"{turn:>4} | {' | '.join(cells)} | {' '.join(moves)}"

    def show(self) -> None:
        """Print the header, then one row per turn."""
        print(self.header())
        for turn in range(1, self.simulation.total_turns + 1):
            print(self.render_turn(turn))
