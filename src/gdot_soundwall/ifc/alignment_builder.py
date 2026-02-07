"""Build IfcAlignment with horizontal and vertical segment hierarchies from LandXML data."""
from __future__ import annotations

import math
from typing import Optional

import ifcopenshell.guid

from gdot_soundwall.ifc.project_setup import IfcProjectContext
from gdot_soundwall.ifc.geometry_builder import create_placement
from gdot_soundwall.landxml.alignment import (
    HorizontalAlignment, LineSegment, ArcSegment, SpiralSegment,
)
from gdot_soundwall.landxml.profile import VerticalProfile


def build_alignment(
    ctx: IfcProjectContext,
    h_alignment: HorizontalAlignment,
    v_profile: Optional[VerticalProfile] = None,
) -> object:
    """Create an IfcAlignment entity with horizontal and vertical layouts.

    Args:
        ctx: IFC project context.
        h_alignment: Parsed horizontal alignment.
        v_profile: Optional parsed vertical profile.

    Returns:
        IfcAlignment entity.
    """
    f = ctx.file
    guid = ifcopenshell.guid.new

    # Create the IfcAlignment
    if h_alignment.segments:
        first_seg = h_alignment.segments[0]
        placement = create_placement(
            ctx,
            first_seg.start_easting,
            first_seg.start_northing,
            0.0,
        )
    else:
        placement = create_placement(ctx, 0.0, 0.0, 0.0)

    alignment = f.create_entity("IfcAlignment",
                                GlobalId=guid(),
                                OwnerHistory=ctx.owner_history,
                                Name=h_alignment.name or "SoundWall Alignment",
                                ObjectPlacement=placement)

    # ── Horizontal Alignment ──────────────────────────────────────
    h_segments = _build_horizontal_segments(ctx, h_alignment)
    if h_segments:
        h_align = f.create_entity("IfcAlignmentHorizontal",
                                  GlobalId=guid(),
                                  OwnerHistory=ctx.owner_history,
                                  Name="Horizontal")

        # Nest horizontal segments
        f.create_entity("IfcRelNests",
                        GlobalId=guid(),
                        OwnerHistory=ctx.owner_history,
                        RelatingObject=h_align,
                        RelatedObjects=h_segments)

        # Nest horizontal under alignment
        f.create_entity("IfcRelNests",
                        GlobalId=guid(),
                        OwnerHistory=ctx.owner_history,
                        RelatingObject=alignment,
                        RelatedObjects=[h_align])

    # ── Vertical Alignment ────────────────────────────────────────
    if v_profile and v_profile.pvis:
        v_segments = _build_vertical_segments(ctx, v_profile)
        if v_segments:
            v_align = f.create_entity("IfcAlignmentVertical",
                                      GlobalId=guid(),
                                      OwnerHistory=ctx.owner_history,
                                      Name="Vertical")

            f.create_entity("IfcRelNests",
                            GlobalId=guid(),
                            OwnerHistory=ctx.owner_history,
                            RelatingObject=v_align,
                            RelatedObjects=v_segments)

            # Get existing nested objects from alignment
            nested = [h_align] if h_segments else []
            nested.append(v_align)

            # Re-create the nesting if we already have horizontal
            if h_segments:
                # Find and update existing rel
                for rel in f.by_type("IfcRelNests"):
                    if rel.RelatingObject == alignment:
                        rel.RelatedObjects = nested
                        break
            else:
                f.create_entity("IfcRelNests",
                                GlobalId=guid(),
                                OwnerHistory=ctx.owner_history,
                                RelatingObject=alignment,
                                RelatedObjects=nested)

    return alignment


def _build_horizontal_segments(
    ctx: IfcProjectContext,
    h_alignment: HorizontalAlignment,
) -> list:
    """Create IfcAlignmentSegment entities for each horizontal segment."""
    f = ctx.file
    guid = ifcopenshell.guid.new
    segments = []

    for seg in h_alignment.segments:
        # Create the design parameters based on segment type
        if isinstance(seg, LineSegment):
            design_params = f.create_entity(
                "IfcAlignmentHorizontalSegment",
                StartPoint=f.create_entity("IfcCartesianPoint",
                                          Coordinates=[seg.start_easting,
                                                       seg.start_northing]),
                StartDirection=seg.bearing,
                StartRadiusOfCurvature=0.0,
                EndRadiusOfCurvature=0.0,
                SegmentLength=seg.length,
                PredefinedType="LINE",
            )

        elif isinstance(seg, ArcSegment):
            r = seg.radius if seg.is_clockwise else -seg.radius
            design_params = f.create_entity(
                "IfcAlignmentHorizontalSegment",
                StartPoint=f.create_entity("IfcCartesianPoint",
                                          Coordinates=[seg.start_easting,
                                                       seg.start_northing]),
                StartDirection=seg.start_bearing,
                StartRadiusOfCurvature=r,
                EndRadiusOfCurvature=r,
                SegmentLength=seg.length,
                PredefinedType="CIRCULARARC",
            )

        elif isinstance(seg, SpiralSegment):
            r_start = seg.start_radius if not math.isinf(seg.start_radius) else 0.0
            r_end = seg.end_radius if not math.isinf(seg.end_radius) else 0.0
            if not seg.is_clockwise:
                r_start = -r_start
                r_end = -r_end
            design_params = f.create_entity(
                "IfcAlignmentHorizontalSegment",
                StartPoint=f.create_entity("IfcCartesianPoint",
                                          Coordinates=[seg.start_easting,
                                                       seg.start_northing]),
                StartDirection=seg.start_bearing,
                StartRadiusOfCurvature=r_start,
                EndRadiusOfCurvature=r_end,
                SegmentLength=seg.length,
                PredefinedType="CLOTHOID",
            )
        else:
            continue

        align_seg = f.create_entity("IfcAlignmentSegment",
                                    GlobalId=guid(),
                                    OwnerHistory=ctx.owner_history,
                                    DesignParameters=design_params)
        segments.append(align_seg)

    return segments


def _build_vertical_segments(
    ctx: IfcProjectContext,
    v_profile: VerticalProfile,
) -> list:
    """Create IfcAlignmentSegment entities for vertical profile."""
    f = ctx.file
    guid = ifcopenshell.guid.new
    segments = []

    for i in range(len(v_profile.pvis) - 1):
        pvi1 = v_profile.pvis[i]
        pvi2 = v_profile.pvis[i + 1]

        length = pvi2.station - pvi1.station
        grade = (pvi2.elevation - pvi1.elevation) / length if length > 0 else 0.0

        if pvi2.has_curve:
            pred_type = "PARABOLICARC"
        else:
            pred_type = "CONSTANTGRADIENT"

        design_params = f.create_entity(
            "IfcAlignmentVerticalSegment",
            StartDistAlong=pvi1.station,
            HorizontalLength=length,
            StartHeight=pvi1.elevation,
            StartGradient=grade,
            EndGradient=grade,
            PredefinedType=pred_type,
        )

        align_seg = f.create_entity("IfcAlignmentSegment",
                                    GlobalId=guid(),
                                    OwnerHistory=ctx.owner_history,
                                    DesignParameters=design_params)
        segments.append(align_seg)

    return segments
