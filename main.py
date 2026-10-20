"""Entry point: python3 main.py <map_file>."""

import sys
from parser import MapParser, ParseError

from pathfinding import PathError, PathFinder
from simulation import Simulation, SimulationError
from visualizer import Visualizer


def main() -> int:
    """Run parser, pathfinder and simulation; return the exit code."""
    # --- Level 2 (animation): disabled ---
    # usage = "Usage: python3 main.py <map_file> [--animate]"
    # if len(sys.argv) not in (2, 3) or (
    #     len(sys.argv) == 3 and sys.argv[2] != "--animate"
    # ):
    usage = "Usage: python3 main.py <map_file>"
    if len(sys.argv) != 2:
        print(usage, file=sys.stderr)
        return 1
    try:
        graph, nb_drones = MapParser().parse(sys.argv[1])
        paths = PathFinder(graph, nb_drones).plan_all()
        simulation = Simulation(graph, paths)
        lines = simulation.run()
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error: cannot read file: {e}", file=sys.stderr)
        return 1
    except ParseError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except PathError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except SimulationError as e:
        print(f"Error: invalid plan: {e}", file=sys.stderr)
        return 1
    for line in lines:
        print(line)
    print(simulation.metrics())
    visualizer = Visualizer(simulation)
    # --- Level 2 (animation): disabled ---
    # if len(sys.argv) == 3:
    #     visualizer.animate()
    # else:
    print("=== Visualization ===")
    visualizer.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
