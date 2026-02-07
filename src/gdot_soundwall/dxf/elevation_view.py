"""Profile/elevation view DXF generation.

Draws a side view with station on X-axis and elevation on Y-axis,
showing panels, posts, footings, and the ground profile.
"""
from __future__ import annotations

from typing import Optional

import ezdxf
from ezdxf.document import Drawing

from gdot_soundwall.model.wall_assembly import WallLayout
from gdot_soundwall.landxml.profile import VerticalProfile


# Vertical exaggeration / offset for the elevation view
VIEW_OFFSET_X = 0.0
VIEW_OFFSET_Y = -20.0  # Draw below plan view


def draw_elevation_view(
    doc: Drawing,
    layout: WallLayout,
    profile: Optional[VerticalProfile] = None,
    x_offset: float = VIEW_OFFSET_X,
    y_offset: float = VIEW_OFFSET_Y,
) -> None:
    """Draw elevation (profile) view of the wall."""
    msp = doc.modelspace()

    def tx(station: float) -> float:
        return station + x_offset

    def ty(elevation: float) -> float:
        return elevation + y_offset

    # ── Ground Profile Line ───────────────────────────────────────
    if profile and profile.pvis:
        ground_pts = []
        num_pts = max(50, int(layout.total_length / 1.0))
        for i in range(num_pts + 1):
            sta = layout.start_station + i * layout.total_length / num_pts
            elev = profile.elevation_at_station(sta)
            ground_pts.append((tx(sta), ty(elev)))

        if len(ground_pts) >= 2:
            msp.add_lwpolyline(ground_pts, dxfattribs={
                "layer": "ELEV_GROUND", "color": 8,  # Gray
            })

    # ── Posts (vertical lines) ────────────────────────────────────
    for post in layout.posts:
        msp.add_line(
            start=(tx(post.station), ty(post.ground_elevation)),
            end=(tx(post.station), ty(post.top_elevation)),
            dxfattribs={"layer": "ELEV_POSTS", "color": 5},
        )

    # ── Panels (rectangles in elevation) ──────────────────────────
    for panel in layout.panels:
        sta_left = panel.station_start
        sta_right = panel.station_end
        bot = panel.bottom_elevation
        top = panel.top_elevation

        pts = [
            (tx(sta_left), ty(bot)),
            (tx(sta_right), ty(bot)),
            (tx(sta_right), ty(top)),
            (tx(sta_left), ty(top)),
            (tx(sta_left), ty(bot)),
        ]
        msp.add_lwpolyline(pts, dxfattribs={
            "layer": "ELEV_PANELS", "color": 3,
        })

    # ── Footings ──────────────────────────────────────────────────
    for ftg in layout.footings:
        half_w = (ftg.diameter / 2.0 if ftg.diameter > 0
                  else ftg.length / 2.0 if ftg.length > 0 else 0.3)
        top = ftg.top_elevation
        bot = ftg.bottom_elevation

        pts = [
            (tx(ftg.station - half_w), ty(top)),
            (tx(ftg.station + half_w), ty(top)),
            (tx(ftg.station + half_w), ty(bot)),
            (tx(ftg.station - half_w), ty(bot)),
            (tx(ftg.station - half_w), ty(top)),
        ]
        msp.add_lwpolyline(pts, dxfattribs={
            "layer": "ELEV_FOOTINGS", "color": 4,
        })

    # ── Caps ──────────────────────────────────────────────────────
    for cap in layout.caps:
        pts = [
            (tx(cap.station_start), ty(cap.bottom_elevation)),
            (tx(cap.station_end), ty(cap.bottom_elevation)),
            (tx(cap.station_end), ty(cap.top_elevation)),
            (tx(cap.station_start), ty(cap.top_elevation)),
            (tx(cap.station_start), ty(cap.bottom_elevation)),
        ]
        msp.add_lwpolyline(pts, dxfattribs={
            "layer": "ELEV_CAPS", "color": 2,  # Yellow
        })

    # ── Joints (vertical dashed indicators) ───────────────────────
    for joint in layout.joints:
        msp.add_line(
            start=(tx(joint.station), ty(joint.ground_elevation)),
            end=(tx(joint.station), ty(joint.top_elevation)),
            dxfattribs={
                "layer": "ELEV_JOINTS",
                "color": 1 if joint.joint_type.value == "expansion" else 6,
                "linetype": "DASHED",
            },
        )
