"""Simplified map parser for drone routing configurations."""

from models import Connection, Graph, Zone, ZoneType


class ParseError(Exception):
    """Raised when the map file contains invalid formatting or syntax."""

    def __init__(self, message: str, line_num: int | None = None) -> None:
        """Prefix the message with the line number when one is given."""
        super().__init__(
            f"Line {line_num}: {message}" if line_num is not None else message
        )


class MapParser:
    """Read a map file and build the corresponding Graph."""

    ZONE_TAGS = {"zone", "color", "max_drones"}
    CONNECTION_TAGS = {"max_link_capacity"}

    def __init__(self) -> None:
        """Start with an empty graph and no drones."""
        self.graph = Graph()
        self.nb_drones = 0

    def parse(self, path: str) -> tuple[Graph, int]:
        """Read the map file and return the graph and the number of drones."""
        handlers = {
            "nb_drones": self.parse_nb_drones,
            "start_hub": self.parse_zone,
            "end_hub": self.parse_zone,
            "hub": self.parse_zone,
            "connection": self.parse_connection,
        }
        with open(path, encoding="utf-8") as file:
            for line_num, raw_line in enumerate(file, start=1):
                line = raw_line.split("#", 1)[0].strip()
                if not line:
                    continue
                prefix, sep, rest = line.partition(":")
                prefix = prefix.strip()
                handler = handlers.get(prefix)
                if not sep or handler is None:
                    raise ParseError(f"unknown line '{line}'", line_num)
                if self.nb_drones == 0 and prefix != "nb_drones":
                    raise ParseError("first line must be nb_drones", line_num)
                handler(prefix, rest.strip(), line_num)

        if self.nb_drones == 0:
            raise ParseError("empty map: missing nb_drones")
        if not self.graph.start:
            raise ParseError("missing start_hub")
        if not self.graph.end:
            raise ParseError("missing end_hub")
        for name in (self.graph.start, self.graph.end):
            if self.graph.zones[name].zone_type is ZoneType.BLOCKED:
                raise ParseError(f"zone '{name}' cannot be blocked")
        return self.graph, self.nb_drones

    def positive_int(self, value: str, what: str, line_num: int) -> int:
        """Convert value to an int greater than 0 or raise ParseError."""
        try:
            number = int(value)
        except ValueError:
            raise ParseError(f"invalid {what} '{value}'", line_num) from None
        if number <= 0:
            raise ParseError(f"{what} must be greater than 0", line_num)
        return number

    def split_metadata(
        self, rest: str, allowed: set[str], line_num: int
    ) -> tuple[str, dict[str, str]]:
        """Split '<main> [k=v ...]' into the main part and a tag dict."""
        main, bracket, meta = rest.partition("[")
        if "]" in main:
            raise ParseError("unexpected ']' without matching '['", line_num)
        if not bracket:
            return main, {}

        meta = meta.strip()
        if not meta.endswith("]"):
            raise ParseError("metadata block is missing closing ']'", line_num)
        inner = meta[:-1]
        if "[" in inner or "]" in inner:
            raise ParseError(
                "only one metadata block '[...]' is allowed", line_num
            )

        tags: dict[str, str] = {}
        for tag in inner.split():
            key, _, value = tag.partition("=")
            if not key or not value:
                raise ParseError(
                    f"invalid tag '{tag}', expected 'key=value'", line_num
                )
            if key not in allowed:
                expected = ", ".join(sorted(allowed))
                raise ParseError(
                    f"unknown tag '{key}', expected one of: {expected}",
                    line_num,
                )
            if key in tags:
                raise ParseError(f"duplicate tag '{key}'", line_num)
            tags[key] = value
        return main, tags

    def parse_nb_drones(self, prefix: str, rest: str, line_num: int) -> None:
        """Parse the number of drones and validate it."""
        if self.nb_drones != 0:
            raise ParseError("duplicate nb_drones line", line_num)
        self.nb_drones = self.positive_int(rest, "number of drones", line_num)

    def parse_zone(self, prefix: str, rest: str, line_num: int) -> None:
        """Parse a zone line and add the zone to the graph."""
        main, meta = self.split_metadata(rest, self.ZONE_TAGS, line_num)

        parts = main.split()
        if len(parts) != 3:
            raise ParseError(
                f"expected '<name> <x> <y>', got '{main.strip()}'", line_num
            )
        name, x_str, y_str = parts
        if "-" in name:
            raise ParseError(
                f"zone name '{name}' must not contain '-'", line_num
            )
        if name in self.graph.zones:
            raise ParseError(f"duplicate zone name '{name}'", line_num)
        try:
            x, y = int(x_str), int(y_str)
        except ValueError:
            raise ParseError(
                f"invalid coordinates '{x_str} {y_str}'", line_num
            ) from None

        if prefix == "start_hub" and self.graph.start:
            raise ParseError("duplicate start_hub", line_num)
        if prefix == "end_hub" and self.graph.end:
            raise ParseError("duplicate end_hub", line_num)

        zone_str = meta.get("zone", "normal")
        try:
            zone_type = ZoneType(zone_str)
        except ValueError:
            raise ParseError(
                f"invalid zone type '{zone_str}'", line_num
            ) from None

        max_drones = (
            self.nb_drones
            if prefix in ("start_hub", "end_hub")
            else self.positive_int(
                meta.get("max_drones", "1"), "max_drones", line_num
            )
        )

        self.graph.add_zone(
            Zone(
                name,
                x,
                y,
                zone_type=zone_type,
                color=meta.get("color"),
                max_drones=max_drones,
            )
        )
        if prefix == "start_hub":
            self.graph.start = name
        elif prefix == "end_hub":
            self.graph.end = name

    def parse_connection(
        self, prefix: str, rest: str, line_num: int
    ) -> None:
        """Parse a connection line and add the link to the graph."""
        main, meta = self.split_metadata(
            rest, self.CONNECTION_TAGS, line_num
        )

        parts = main.split()
        names = parts[0].split("-") if len(parts) == 1 else []
        if len(names) != 2 or not all(names):
            raise ParseError(
                f"expected '<zone1>-<zone2>', got '{main.strip()}'", line_num
            )
        zone1, zone2 = names
        if zone1 == zone2:
            raise ParseError(
                f"zone '{zone1}' cannot connect to itself", line_num
            )
        for name in names:
            if name not in self.graph.zones:
                raise ParseError(f"unknown zone '{name}'", line_num)
        if Connection.key(zone1, zone2) in self.graph.connections:
            raise ParseError(
                f"duplicate connection '{zone1}-{zone2}'", line_num
            )

        capacity = self.positive_int(
            meta.get("max_link_capacity", "1"), "max_link_capacity", line_num
        )
        self.graph.add_connection(
            Connection(zone1, zone2, max_link_capacity=capacity)
        )
