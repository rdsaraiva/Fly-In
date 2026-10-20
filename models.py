"""Data models for the Fly-in drone routing graph."""

from dataclasses import dataclass, field
from enum import Enum

ConnectionKey = frozenset[str]


class ZoneType(Enum):
    """Zone type; each value is the exact string used in the map file."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


@dataclass
class Zone:
    """A node of the graph where drones can stay.

    Attributes:
        name: Unique zone name.
        x: Horizontal coordinate.
        y: Vertical coordinate.
        zone_type: Movement rules applied when entering the zone.
        color: Optional display color.
        max_drones: Max drones in the zone at the same time.
    """

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1

    @property
    def move_cost(self) -> int:
        """Return the number of turns needed to enter this zone."""
        return 2 if self.zone_type is ZoneType.RESTRICTED else 1


@dataclass
class Connection:
    """A bidirectional edge between two zones.

    Attributes:
        zone_a: Name of the first zone.
        zone_b: Name of the second zone.
        max_link_capacity: Max drones traversing it at the same time.
    """

    zone_a: str
    zone_b: str
    max_link_capacity: int = 1

    @staticmethod
    def key(a: str, b: str) -> ConnectionKey:
        """Return an order-independent key for the pair (a, b)."""
        return frozenset((a, b))


@dataclass
class Graph:
    """Network of zones linked by bidirectional connections.

    Attributes:
        start: Name of the start zone.
        end: Name of the end zone.
        zones: Zones indexed by name.
        connections: Connections indexed by their order-independent key.
        adjacency: Neighbor names of each zone.
    """

    start: str = ""
    end: str = ""
    zones: dict[str, Zone] = field(default_factory=dict)
    connections: dict[ConnectionKey, Connection] = field(
        default_factory=dict
    )
    adjacency: dict[str, set[str]] = field(default_factory=dict)

    def add_zone(self, zone: Zone) -> None:
        """Register a zone with an empty neighbor set."""
        self.zones[zone.name] = zone
        self.adjacency[zone.name] = set()

    def add_connection(self, connection: Connection) -> None:
        """Register a connection in both directions.

        Both zones must already exist; the parser validates this.
        """
        a, b = connection.zone_a, connection.zone_b
        self.connections[Connection.key(a, b)] = connection
        self.adjacency[a].add(b)
        self.adjacency[b].add(a)

    def get_neighbors(self, name: str) -> set[str]:
        """Return the names of the zones connected to `name`."""
        return self.adjacency.get(name, set())
