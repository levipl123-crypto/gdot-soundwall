"""DXF export orchestrator - combines plan, elevation, and section views."""
from __future__ import annotations

from typing import List, Optional

import ezdxf

from gdot_soundwall.model.wall_assembly import WallLayout
from gdot_soundwall.landxml.alignment import HorizontalAlignment
from gdot_soundwall.landxml.profile import VerticalProfile
from gdot_soundwall.dxf.plan_view import draw_plan_view
from gdot_soundwall.dxf.elevation_view import draw_elevation_view
from gdot_soundwall.dxf.section_view import draw_section_views


# Layer definitions: (name, color, linetype)
LAYERS = [
    ("ALIGNMENT_CL", 1, "CONTINUOUS"),
    ("POSTS", 5, "CONTINUOUS"),
    ("PANELS", 3, "CONTINUOUS"),
    ("FOOTINGS", 4, "CONTINUOUS"),
    ("JOINTS", 1, "DASHED"),
    ("LABELS", 7, "CONTINUOUS"),
    ("ELEV_GROUND", 8, "CONTINUOUS"),
    ("ELEV_POSTS", 5, "CONTINUOUS"),
    ("ELEV_PANELS", 3, "CONTINUOUS"),
    ("ELEV_FOOTINGS", 4, "CONTINUOUS"),
    ("ELEV_CAPS", 2, "CONTINUOUS"),
    ("ELEV_JOINTS", 1, "DASHED"),
    ("SECTION_LABELS", 7, "CONTINUOUS"),
    ("SECTION_GROUND", 8, "CONTINUOUS"),
    ("SECTION_POST", 5, "CONTINUOUS"),
    ("SECTION_PANEL", 3, "CONTINUOUS"),
    ("SECTION_CAP", 2, "CONTINUOUS"),
    ("SECTION_FOOTING", 4, "CONTINUOUS"),
]


def export_dxf(
    layout: WallLayout,
    alignment: HorizontalAlignment,
    profile: Optional[VerticalProfile] = None,
    output_path: str = "soundwall.dxf",
    section_stations: Optional[List[float]] = None,
) -> None:
    """Export wall layout to DXF file with plan, elevation, and section views.

    Args:
        layout: Computed wall layout.
        alignment: Horizontal alignment data.
        profile: Optional vertical profile.
        output_path: Output DXF file path.
        section_stations: Stations for cross-section views.
    """
    doc = ezdxf.new("R2013")

    # Set up layers
    for name, color, linetype in LAYERS:
        if linetype == "DASHED" and "DASHED" not in doc.linetypes:
            doc.linetypes.add("DASHED", pattern=[0.5, 0.25, -0.25])
        doc.layers.add(name, color=color,
                       linetype=linetype if linetype in doc.linetypes else "CONTINUOUS")

    # Draw views
    draw_plan_view(doc, layout, alignment)
    draw_elevation_view(doc, layout, profile)
    draw_section_views(doc, layout, section_stations)

    doc.saveas(output_path)
