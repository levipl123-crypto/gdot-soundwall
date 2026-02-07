"""Cross-section views at specified stations."""
from __future__ import annotations

import math
from typing import List, Optional

import ezdxf
from ezdxf.document import Drawing

from gdot_soundwall import config
from gdot_soundwall.model.wall_assembly import WallLayout


# Default offset for section views
SECTION_OFFSET_X = 0.0
SECTION_OFFSET_Y = -50.0


def draw_section_views(
    doc: Drawing,
    layout: WallLayout,
    stations: Optional[List[float]] = None,
    x_offset: float = SECTION_OFFSET_X,
    y_offset: float = SECTION_OFFSET_Y,
) -> None:
    """Draw cross-section views at specified stations.

    If no stations specified, draws sections at start, middle, and end.
    """
    msp = doc.modelspace()

    if stations is None:
        mid = (layout.start_station + layout.end_station) / 2.0
        stations = [layout.start_station + 5.0, mid, layout.end_station - 5.0]

    section_spacing = 15.0  # Spacing between section drawings

    for idx, target_sta in enumerate(stations):
        ox = x_offset + idx * section_spacing
        oy = y_offset

        # Find nearest bay
        bay = None
        for b in layout.bays:
            if b.post_left.station <= target_sta <= b.post_right.station:
                bay = b
                break
        if bay is None and layout.bays:
            bay = layout.bays[0]
        if bay is None:
            continue

        ground_elev = (bay.post_left.ground_elevation + bay.post_right.ground_elevation) / 2.0

        # Section title
        msp.add_text(
            f"Section @ Sta {target_sta:.1f}m",
            dxfattribs={"layer": "SECTION_LABELS", "height": 0.25, "color": 7},
        ).set_placement((ox - 2, oy + ground_elev + layout.wall_height + 1.5))

        # Ground line
        msp.add_line(
            start=(ox - 3, oy + ground_elev),
            end=(ox + 3, oy + ground_elev),
            dxfattribs={"layer": "SECTION_GROUND", "color": 8},
        )

        # Post cross-section (I-shape simplified as rectangle)
        pw = config.POST_FLANGE_WIDTH
        pd = config.POST_DEPTH
        _draw_rect(msp, ox, oy + ground_elev, ox, oy + ground_elev + layout.wall_height,
                    pw, "SECTION_POST", 5)

        # Panel cross-section
        panel_w = config.PANEL_THICKNESS
        num_panels = len(bay.panels)
        for i in range(num_panels):
            bot = ground_elev + i * config.PANEL_HEIGHT
            top = bot + config.PANEL_HEIGHT
            pts = [
                (ox - panel_w / 2, oy + bot),
                (ox + panel_w / 2, oy + bot),
                (ox + panel_w / 2, oy + top),
                (ox - panel_w / 2, oy + top),
                (ox - panel_w / 2, oy + bot),
            ]
            msp.add_lwpolyline(pts, dxfattribs={
                "layer": "SECTION_PANEL", "color": 3,
            })

        # Cap
        if bay.cap:
            cap_w = bay.cap.depth
            cap_bot = bay.cap.bottom_elevation
            cap_top = bay.cap.top_elevation
            pts = [
                (ox - cap_w / 2, oy + cap_bot),
                (ox + cap_w / 2, oy + cap_bot),
                (ox + cap_w / 2, oy + cap_top),
                (ox - cap_w / 2, oy + cap_top),
                (ox - cap_w / 2, oy + cap_bot),
            ]
            msp.add_lwpolyline(pts, dxfattribs={
                "layer": "SECTION_CAP", "color": 2,
            })

        # Footing
        if bay.footing_left:
            ftg = bay.footing_left
            if ftg.diameter > 0:
                # Caisson shown as rectangle in section
                r = ftg.diameter / 2.0
                pts = [
                    (ox - r, oy + ftg.top_elevation),
                    (ox + r, oy + ftg.top_elevation),
                    (ox + r, oy + ftg.bottom_elevation),
                    (ox - r, oy + ftg.bottom_elevation),
                    (ox - r, oy + ftg.top_elevation),
                ]
            else:
                hw = ftg.width / 2.0
                pts = [
                    (ox - hw, oy + ftg.top_elevation),
                    (ox + hw, oy + ftg.top_elevation),
                    (ox + hw, oy + ftg.bottom_elevation),
                    (ox - hw, oy + ftg.bottom_elevation),
                    (ox - hw, oy + ftg.top_elevation),
                ]
            msp.add_lwpolyline(pts, dxfattribs={
                "layer": "SECTION_FOOTING", "color": 4,
            })


def _draw_rect(msp, cx: float, bot_y: float, _cx: float, top_y: float,
               width: float, layer: str, color: int) -> None:
    """Draw a centered rectangle."""
    hw = width / 2.0
    pts = [(cx - hw, bot_y), (cx + hw, bot_y),
           (cx + hw, top_y), (cx - hw, top_y), (cx - hw, bot_y)]
    msp.add_lwpolyline(pts, dxfattribs={"layer": layer, "color": color})
