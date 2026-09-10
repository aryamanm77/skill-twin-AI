"""
Workspace zone system.

Zones are defined in normalized [0,1]x[0,1] coordinates matching the
homography output (or directly as normalized pixel fractions if uncalibrated).
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Zone:
    id: str
    name: str
    color: str
    # Normalized bounding box: x, y (top-left), w, h
    x: float
    y: float
    w: float
    h: float


class ZoneChecker:
    """Checks if a normalized point falls within any configured zone."""

    def __init__(self, zones: List[Zone]):
        self.zones = {z.id: z for z in zones}

    def check(self, nx: float, ny: float) -> List[str]:
        """Return IDs of zones containing the normalized point (nx, ny)."""
        result = []
        for zid, z in self.zones.items():
            if z.x <= nx <= z.x + z.w and z.y <= ny <= z.y + z.h:
                result.append(zid)
        return result

    def is_in_zone(self, nx: float, ny: float, zone_id: str) -> bool:
        z = self.zones.get(zone_id)
        if not z:
            return False
        return z.x <= nx <= z.x + z.w and z.y <= ny <= z.y + z.h

    def get_zone(self, zone_id: str) -> Optional[Zone]:
        return self.zones.get(zone_id)

    def all_zones(self) -> List[Zone]:
        return list(self.zones.values())


def zones_from_procedure(procedure_config: dict) -> ZoneChecker:
    """Build a ZoneChecker from procedure JSON config."""
    zones = []
    for z in procedure_config.get("workspace_zones", []):
        norm = z.get("normalized", {})
        zones.append(Zone(
            id=z["id"], name=z["name"], color=z.get("color", "#999"),
            x=norm.get("x", 0), y=norm.get("y", 0),
            w=norm.get("w", 0.2), h=norm.get("h", 0.2),
        ))
    return ZoneChecker(zones)
