"""Top-down plan view DXF generation."""
from __future__ import annotations

import math
from typing import Optional

import ezdxf
from ezdxf.document import Drawing

from gdot_soundwall.model.wall_assembly import WallLayout
from gdot_soundwall.landxml.alignment import HorizontalAlignment
from gdot_soundwall.utils.math_helpers import offset_point


def draw_plan_view(
    doc: Drawing,
    layout: WallLayout,
    alignment: HorizontalAlignment,
) -> None:
    """Draw plan view (top-down) of wall components."""
    msp = doc.modelspace()

    # ── Alignment centerline ──────────────────────────────────────
    alignment_points = []
    for seg in alignment.segments:
        num_pts = max(2, int(seg.length / 1.0))
        for i in range(num_pts + 1):
            sta = seg.start_station + i * seg.length / num_pts
            e, n, _ = seg.point_at_station(min(sta, seg.end_station))
            alignment_points.append((e, n))

    if len(alignment_points) >= 2:
        msp.add_lwpolyline(alignment_points, dxfattribs={
            "layer": "ALIGNMENT_CL",
            "color": 1,  # Red
        })

    # ── Posts (circles) ───────────────────────────────────────────
    for post in layout.posts:
        msp.add_circle(
            center=(post.easting, post.northing),
            radius=post.flange_width / 2.0,
            dxfattribs={"layer": "POSTS", "color": 5},  # Blue
        )
        # Post label
        msp.add_text(
            f"P{post.index}",
            dxfattribs={
                "layer": "LABELS",
                "height": 0.3,
                "color": 7,
            },
        ).set_placement((post.easting + 0.3, post.northing + 0.3))

    # ── Panels (rectangles) ───────────────────────────────────────
    for panel in layout.panels:
        if panel.stack_index > 0:
            continue  # Only draw bottom panel in plan
        _draw_rotated_rect(
            msp, panel.easting, panel.northing,
            panel.width, panel.thickness, panel.bearing,
            layer="PANELS", color=3,  # Green
        )

    # ── Footings ──────────────────────────────────────────────────
    for ftg in layout.footings:
        if ftg.diameter > 0:
            msp.add_circle(
                center=(ftg.easting, ftg.northing),
                radius=ftg.diameter / 2.0,
                dxfattribs={"layer": "FOOTINGS", "color": 4},  # Cyan
            )
        elif ftg.width > 0:
            _draw_rotated_rect(
                msp, ftg.easting, ftg.northing,
                ftg.length, ftg.width, ftg.bearing,
                layer="FOOTINGS", color=4,
            )

    # ── Joints (diamonds) ─────────────────────────────────────────
    for joint in layout.joints:
        size = 0.3
        pts = [
            (joint.easting, joint.northing + size),
            (joint.easting + size, joint.northing),
            (joint.easting, joint.northing - size),
            (joint.easting - size, joint.northing),
            (joint.easting, joint.northing + size),
        ]
        color = 1 if joint.joint_type.value == "expansion" else 6
        msp.add_lwpolyline(pts, dxfattribs={
            "layer": "JOINTS", "color": color,
        })


def _draw_rotated_rect(
    msp, cx: float, cy: float,
    width: float, depth: float, bearing: float,
    layer: str = "0", color: int = 7,
) -> None:
    """Draw a rotated rectangle in plan view."""
    hw = width / 2.0
    hd = depth / 2.0

    # Corners in local coordinates (along-wall, across-wall)
    local_corners = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd), (-hw, -hd)]

    cos_b = math.cos(bearing)
    sin_b = math.sin(bearing)

    points = []
    for lx, ly in local_corners:
        # Rotate: local X along bearing (sin,cos), local Y perpendicular
        gx = cx + lx * sin_b + ly * cos_b
        gy = cy + lx * cos_b - ly * sin_b
        points.append((gx, gy))

    msp.add_lwpolyline(points, dxfattribs={"layer": layer, "color": color})
