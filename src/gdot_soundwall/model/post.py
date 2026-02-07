"""Steel post dataclass."""
from __future__ import annotations

from dataclasses import dataclass

from gdot_soundwall import config


@dataclass
class SteelPost:
    """A single steel H-post in the sound wall."""
    index: int
    station: float                # Station along alignment (meters)
    easting: float
    northing: float
    ground_elevation: float       # Ground elevation at post location
    top_elevation: float          # Top of post elevation
    bearing: float                # Alignment bearing at station (radians)
    height: float                 # Total post height above ground

    # Post profile (from config, but stored for convenience)
    section: str = config.POST_SECTION
    flange_width: float = config.POST_FLANGE_WIDTH
    depth: float = config.POST_DEPTH
    web_thickness: float = config.POST_WEB_THICKNESS
    flange_thickness: float = config.POST_FLANGE_THICKNESS

    @property
    def total_length(self) -> float:
        """Total length including embedment in footing."""
        return self.height + config.POST_EMBED_FROM_BOTTOM

    @property
    def bottom_elevation(self) -> float:
        """Bottom of post (within footing)."""
        return self.ground_elevation - config.POST_EMBED_FROM_BOTTOM
