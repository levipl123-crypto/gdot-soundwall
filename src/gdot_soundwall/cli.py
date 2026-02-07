"""Command-line interface for the GDOT Sound Wall Modeling Tool."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gdot_soundwall import __version__, config
from gdot_soundwall.config import WallType, FoundationType
from gdot_soundwall.utils.units import ft_to_m


def parse_args(args=None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="gdot-soundwall",
        description="GDOT Sound Wall Modeling Tool - Generate IFC4.3 models from LandXML alignment data",
    )
    parser.add_argument("input", type=Path,
                        help="Input LandXML file path")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="Output IFC file path (default: <input>.ifc)")
    parser.add_argument("--dxf", type=Path, default=None,
                        help="Optional DXF output file path")
    parser.add_argument("--wall-type", choices=["precast", "mse"],
                        default="precast",
                        help="Wall type: precast (post-and-panel) or mse (MSE composite)")
    parser.add_argument("--wall-height", type=float, default=None,
                        help="Wall height in meters (default: 4.572m / 15ft)")
    parser.add_argument("--wall-height-ft", type=float, default=None,
                        help="Wall height in feet")
    parser.add_argument("--foundation", choices=["caisson", "spread", "continuous"],
                        default="caisson",
                        help="Foundation type (default: caisson)")
    parser.add_argument("--post-spacing", type=float, default=None,
                        help="Post spacing in meters (default: 3.048m / 10ft)")
    parser.add_argument("--post-spacing-ft", type=float, default=None,
                        help="Post spacing in feet")
    parser.add_argument("--start-station", type=float, default=None,
                        help="Start station in meters (default: alignment start)")
    parser.add_argument("--end-station", type=float, default=None,
                        help="End station in meters (default: alignment end)")
    parser.add_argument("--offset", type=float, default=0.0,
                        help="Offset from alignment centerline in meters (positive=right)")
    parser.add_argument("--alignment-name", default="",
                        help="Name of alignment to use (default: first)")
    parser.add_argument("--surface-name", default="",
                        help="Name of surface to use (default: first)")
    parser.add_argument("--project-number", default="",
                        help="GDOT project number for property sets")
    parser.add_argument("--route", default="",
                        help="Route identifier for property sets")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    return parser.parse_args(args)


def main(args=None) -> None:
    """Main entry point."""
    opts = parse_args(args)

    # Validate input
    if not opts.input.exists():
        print(f"Error: Input file not found: {opts.input}", file=sys.stderr)
        sys.exit(1)

    # Resolve output path
    if opts.output is None:
        opts.output = opts.input.with_suffix(".ifc")

    # Resolve wall height
    wall_height = config.DEFAULT_WALL_HEIGHT
    if opts.wall_height is not None:
        wall_height = opts.wall_height
    elif opts.wall_height_ft is not None:
        wall_height = ft_to_m(opts.wall_height_ft)

    # Resolve post spacing
    post_spacing = config.POST_SPACING_MAX
    if opts.post_spacing is not None:
        post_spacing = opts.post_spacing
    elif opts.post_spacing_ft is not None:
        post_spacing = ft_to_m(opts.post_spacing_ft)

    # Resolve wall type
    wall_type = WallType.PRECAST if opts.wall_type == "precast" else WallType.MSE_COMPOSITE

    # Resolve foundation type
    foundation_map = {
        "caisson": FoundationType.CAISSON,
        "spread": FoundationType.SPREAD_FOOTING,
        "continuous": FoundationType.CONTINUOUS_FOOTING,
    }
    foundation_type = foundation_map[opts.foundation]

    print(f"GDOT Sound Wall Modeler v{__version__}")
    print(f"  Input:      {opts.input}")
    print(f"  Output:     {opts.output}")
    print(f"  Wall type:  {wall_type.value}")
    print(f"  Height:     {wall_height:.3f}m ({wall_height / 0.3048:.1f}ft)")
    print(f"  Foundation: {foundation_type.value}")
    print(f"  Spacing:    {post_spacing:.3f}m ({post_spacing / 0.3048:.1f}ft)")
    print()

    # ── Parse LandXML ─────────────────────────────────────────────
    print("Parsing LandXML...")
    from gdot_soundwall.landxml.parser import LandXMLParser

    parser = LandXMLParser(opts.input)
    alignment = parser.parse_alignment(opts.alignment_name)
    profile = parser.parse_profile(opts.alignment_name)
    surface = parser.parse_surface(opts.surface_name)

    print(f"  Alignment:  {alignment.name} ({len(alignment.segments)} segments, "
          f"{alignment.total_length:.1f}m)")
    print(f"  Profile:    {len(profile.pvis)} PVIs")
    print(f"  Surface:    {surface.name} ({surface.num_vertices} vertices, "
          f"{surface.num_triangles} triangles)")

    # ── Compute Layout ────────────────────────────────────────────
    print("Computing wall layout...")
    from gdot_soundwall.geometry.wall_layout import WallLayoutEngine

    engine = WallLayoutEngine(
        alignment=alignment,
        profile=profile,
        surface=surface,
        wall_type=wall_type,
        wall_height=wall_height,
        foundation_type=foundation_type,
        post_spacing=post_spacing,
        start_station=opts.start_station,
        end_station=opts.end_station,
        offset=opts.offset,
    )
    layout = engine.compute()

    print(f"  Posts:      {len(layout.posts)}")
    print(f"  Bays:       {layout.num_bays}")
    print(f"  Panels:     {len(layout.panels)}")
    print(f"  Footings:   {len(layout.footings)}")
    print(f"  Caps:       {len(layout.caps)}")
    print(f"  Joints:     {len(layout.joints)}")
    if layout.mse_segments:
        print(f"  MSE segs:   {len(layout.mse_segments)}")

    # ── Generate IFC ──────────────────────────────────────────────
    print("Generating IFC4.3 model...")
    from gdot_soundwall.ifc.project_setup import create_project
    from gdot_soundwall.ifc.material_builder import build_materials
    from gdot_soundwall.ifc.type_library import build_type_library
    from gdot_soundwall.ifc.alignment_builder import build_alignment
    from gdot_soundwall.ifc.assembly_builder import build_all_assemblies
    from gdot_soundwall.ifc.mse_builder import build_all_mse_segments
    from gdot_soundwall.ifc.pset_builder import attach_general_pset
    from gdot_soundwall.ifc.spatial_structure import contain_in_facility

    ctx = create_project(
        project_name=f"GDOT Sound Wall - {opts.project_number}" if opts.project_number else "GDOT Sound Wall",
        project_number=opts.project_number,
        route=opts.route,
    )

    mat_lib = build_materials(ctx)
    type_lib = build_type_library(ctx)

    # Build alignment
    ifc_alignment = build_alignment(ctx, alignment, profile)
    contain_in_facility(ctx, [ifc_alignment])

    # Build assemblies
    assemblies = build_all_assemblies(ctx, layout, type_lib, mat_lib)

    # Attach general pset to first assembly (or facility)
    if assemblies:
        attach_general_pset(ctx, ctx.facility, layout,
                            opts.project_number, opts.route)

    # Build MSE segments if applicable
    if layout.mse_segments:
        build_all_mse_segments(ctx, layout.mse_segments, mat_lib)

    # Write IFC file
    ctx.file.write(str(opts.output))
    print(f"  Written: {opts.output}")

    # Count entities
    total_entities = len(list(ctx.file))
    print(f"  Entities: {total_entities}")

    # ── Optional DXF Export ───────────────────────────────────────
    if opts.dxf:
        print("Generating DXF...")
        from gdot_soundwall.dxf.exporter import export_dxf
        export_dxf(layout, alignment, profile, str(opts.dxf))
        print(f"  Written: {opts.dxf}")

    print("\nDone.")
