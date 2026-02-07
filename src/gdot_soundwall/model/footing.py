"""Foundation dataclasses."""
from __future__ import annotations

from dataclasses import dataclass

from gdot_soundwall import config
from gdot_soundwall.config import FoundationType


@dataclass
class Footing:
    """Base footing for a sound wall post."""
    post_index: int
    foundation_type: FoundationType
    station: float
    easting: float
    northing: float
    top_elevation: float          # Top of footing (ground level)
    bearing: float

    # Dimensions (set based on foundation type)
    width: float = 0.0
    length: float = 0.0
    depth: float = 0.0
    diameter: float = 0.0         # For caisson only

    @property
    def bottom_elevation(self) -> float:
        return self.top_elevation - self.depth


def make_caisson(
    post_index: int, station: float, easting: float, northing: float,
    top_elevation: float, bearing: float,
    diameter: float = config.CAISSON_DIAMETER,
    depth: float = config.CAISSON_DEPTH,
) -> Footing:
    """Create a caisson (drilled shaft) footing."""
    return Footing(
        post_index=post_index,
        foundation_type=FoundationType.CAISSON,
        station=station,
        easting=easting,
        northing=northing,
        top_elevation=top_elevation,
        bearing=bearing,
        diameter=diameter,
        depth=depth,
    )


def make_spread_footing(
    post_index: int, station: float, easting: float, northing: float,
    top_elevation: float, bearing: float,
    width: float = config.SPREAD_WIDTH,
    length: float = config.SPREAD_LENGTH,
    depth: float = config.SPREAD_DEPTH,
) -> Footing:
    """Create a spread (pad) footing."""
    return Footing(
        post_index=post_index,
        foundation_type=FoundationType.SPREAD_FOOTING,
        station=station,
        easting=easting,
        northing=northing,
        top_elevation=top_elevation,
        bearing=bearing,
        width=width,
        length=length,
        depth=depth,
    )


def make_continuous_footing(
    post_index: int, station: float, easting: float, northing: float,
    top_elevation: float, bearing: float,
    width: float = config.CONTINUOUS_WIDTH,
    length: float = 3.048,  # One bay length
    depth: float = config.CONTINUOUS_DEPTH,
) -> Footing:
    """Create a continuous (strip) footing."""
    return Footing(
        post_index=post_index,
        foundation_type=FoundationType.CONTINUOUS_FOOTING,
        station=station,
        easting=easting,
        northing=northing,
        top_elevation=top_elevation,
        bearing=bearing,
        width=width,
        length=length,
        depth=depth,
    )
