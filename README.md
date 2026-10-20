*This project has been created as part of the 42 curriculum by roda-fon.*

# Fly-in

## Description

Fly-in is a drone routing simulator. A map describes zones (nodes) linked by
connections (edges). Every drone starts in the start zone, and the goal is to
bring all of them to the end zone in **as few turns as possible** without
breaking any movement or capacity rule.

The program **parses** the map, **plans** a conflict-free path for every
drone, **simulates** the plans turn by turn and **visualizes** them in the
terminal. It only uses the Python standard library.

## Instructions

Requires Python **3.10+**. `flake8` and `mypy` are only needed for linting.

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
python3 main.py <map_file>
```

| Command | What it does |
|---|---|
| `make run` | Runs `maps/example.txt` (`make run MAP=<file>` for another map) |
| `make debug` | Runs the program inside `pdb` |
| `make lint` / `make lint-strict` | `flake8` + `mypy` (subject flags / `--strict`) |
| `make clean` | Removes `__pycache__` and `.mypy_cache` |

To run every map and print only its metrics line:

```bash
for f in maps/*.txt maps/*/*.txt; do echo "$f: $(python3 main.py "$f" | grep Turns)"; done
```

Every error (wrong arguments, unreadable file, invalid map, no path) is
printed on `stderr` with exit code `1`, e.g. `Error: Line 4: invalid zone
type 'lava'`. Map errors always give the line number and the cause.
`maps/invalid/` holds one map per error case (each file starts with a comment
naming its error); to see every message:

```bash
for f in maps/invalid/*.txt; do echo "$f: $(python3 main.py "$f" 2>&1)"; done
```

## Example

Input (`maps/example.txt`):

```
nb_drones: 5
start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: roof2 6 2 [zone=normal color=blue]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
hub: tunnelB 7 4 [zone=normal color=red]
hub: obstacleX 5 5 [zone=blocked color=gray]
connection: hub-roof1
connection: hub-corridorA
connection: roof1-roof2
connection: roof2-goal
connection: corridorA-tunnelB [max_link_capacity=2]
connection: tunnelB-goal
```

Output:

```
D1-corridorA D3-hub-roof1
D1-tunnelB D2-corridorA D3-roof1
D1-goal D2-tunnelB D3-roof2 D4-corridorA
D2-goal D3-goal D4-tunnelB D5-corridorA
D4-goal D5-tunnelB
D5-goal
Turns: 6 | Avg turns/drone: 4.4 | Total moves: 16
```

One line per turn, only drones that move are shown. `D3-hub-roof1` means
drone 3 is on the link to `roof1`: a restricted zone takes 2 turns to enter.

## Algorithm explanation

Drones are planned **one after the other** (prioritized planning). Each drone
takes the path that reaches the end **as early as possible** given what the
previous drones reserved, then reserves its own path. Since every drone
avoids all earlier reservations, the plans have no conflict and no deadlock
by construction.

- **Plan:** `path[t]` is where the drone is at the end of turn `t`: a zone,
  or `"a-b"` while flying to a restricted zone. The output is read directly
  from the plans.
- **Search:** Dijkstra (`heapq`) on the state `(zone, turn)`, so waiting is
  just another move. Cost = `(turn, -priority zones visited)`: the earliest
  arrival wins and, on a tie, the path with more `priority` zones.
- **Moves:** wait (if the zone has room), enter a normal or priority zone in
  1 turn, a restricted zone in 2 turns (only if it has room on arrival, so a
  drone never waits on a link). Blocked zones are never entered.
- **Reservation table:** counters `(zone, turn)` and `(link, turn)`. A link's
  capacity is shared by both directions, and the start and end zones have no
  limit.
- **Search horizon:** last arrival + 2 × number of zones; beyond that there
  is no path, so the search always ends with a clean error.
- **Validation:** `Simulation` replays all plans in a fresh reservation
  table and fails if any zone or link is over capacity.

The approach handles any map without special rules, but it is greedy: an
early drone never gives way to a later one.

**Complexity:** one search is `O((V + E) · T · log(V · T))` (`V` zones, `E`
connections, `T` horizon), so `D` drones cost `D` times that. Only the
reservation table is kept between drones. 500 drones on the example map take
about 0.15 s.

**Results** on the official maps (all within the subject targets):

| Map | Drones | Turns | Target |
|---|---|---|---|
| easy/01 linear path | 2 | 4 | ≤ 6 |
| easy/02 simple fork | 4 | 4 | ≤ 8 |
| easy/03 basic capacity | 4 | 4 | ≤ 6 |
| medium/01 dead end trap | 5 | 8 | ≤ 12 |
| medium/02 circular loop | 6 | 15 | ≤ 15 |
| medium/03 priority puzzle | 5 | 7 | ≤ 12 |
| hard/01 maze nightmare | 8 | 13 | ≤ 30 |
| hard/02 capacity hell | 12 | 16 | ≤ 35 |
| hard/03 ultimate challenge | 15 | 26 | ≤ 45 |
| challenger/01 the impossible dream | 25 | 43 | record: 45 |

## Visual representation

After the required output, the program prints a colored table with one
row per turn (`maps/example.txt`, colors not shown here):

```
=== Visualization ===
Turn | hub | goal | roof1 | roof2 | corridorA | tunnelB | Moves
   1 | 3/5 |  0/5 |   0/1 |   0/1 |       1/2 |     0/1 | D1-corridorA D3-hub-roof1
   2 | 2/5 |  0/5 |   1/1 |   0/1 |       1/2 |     1/1 | D1-tunnelB D2-corridorA D3-roof1
   3 | 1/5 |  1/5 |   0/1 |   1/1 |       1/2 |     1/1 | D1-goal D2-tunnelB D3-roof2 D4-corridorA
```

- Each column is a zone (blocked zones are left out) and each cell is
  `drones/max_drones` at the end of the turn; a full zone is shown in red.
- Zone names and moves use the zone's `color` metadata (unknown colors fall
  back to the default terminal color).
- The `Moves` column shows where each drone went during the turn.

Reading a column from top to bottom shows how a zone fills and empties, so
the bottlenecks of a map and the reason why drones wait are visible at a
glance.

## Project structure

| File | Content |
|---|---|
| `main.py` | Entry point, argument check and error handling |
| `models.py` | `ZoneType`, `Zone`, `Connection`, `Graph` |
| `parser.py` | `MapParser`, `ParseError` |
| `pathfinding.py` | `Reservations`, `PathFinder`, `PathError` |
| `simulation.py` | `Simulation` (validation, output, metrics), `SimulationError` |
| `visualizer.py` | `Visualizer` (colored turn-by-turn table) |
| `maps/` | Example map, the official easy / medium / hard / challenger maps and `invalid/` error maps |

## Resources

- E. W. Dijkstra, *A note on two problems in connexion with graphs*, 1959.
- D. Silver, *Cooperative Pathfinding*, AIIDE 2005 (prioritized planning with
  a space-time reservation table).
- R. Stern et al., *Multi-Agent Pathfinding: Definitions, Variants, and
  Benchmarks*, SoCS 2019.
- Python docs: [`heapq`](https://docs.python.org/3/library/heapq.html),
  [`collections.Counter`](https://docs.python.org/3/library/collections.html#collections.Counter),
  [`dataclasses`](https://docs.python.org/3/library/dataclasses.html).
- [ANSI escape codes](https://en.wikipedia.org/wiki/ANSI_escape_code).

### How AI was used

Claude (Anthropic), through Claude Code, was used as a tutor and reviewer:

- **Planning:** extracting the requirements from the subject and discussing
  design decisions (shared link capacity, planning order, search horizon).
- **Pathfinding:** the approach was designed together with the AI, which
  built a prototype to validate it; I wrote `Reservations` and `PathFinder`
  from signatures and hints.
- **Simulation and main:** written by me; the AI reviewed each version and
  explained the bugs it found.
- **Visualizer:** I wrote it step by step from signatures and hints; when I
  got stuck on the table alignment, the AI showed the corrected methods,
  which I typed in and can explain.
- **Testing:** the AI wrote throw-away test scripts (invalid maps, invalid
  plans, error cases) and ran `flake8` / `mypy`.
- **Written by the AI, reviewed by me:** this README.

Every part of the code was read, tested and understood before being kept.
