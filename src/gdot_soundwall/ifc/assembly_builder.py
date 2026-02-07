"""Build IfcElementAssembly per bay with all child elements.

Each bay (post-to-post span) becomes an IfcElementAssembly containing:
- IfcColumn (steel post)
- IfcWall(s) (stacked panels)
- IfcFooting (foundation)
- IfcPlate (cap/coping)
- IfcBuildingElementProxy (joints, if present)
"""
from __future__ import annotations

from typing import List, Optional

import ifcopenshell.guid

from gdot_soundwall.ifc.project_setup import IfcProjectContext
from gdot_soundwall.ifc.geometry_builder import create_placement
from gdot_soundwall.ifc.type_library import TypeLibrary
from gdot_soundwall.ifc.material_builder import MaterialLibrary
from gdot_soundwall.ifc.post_builder import build_post
from gdot_soundwall.ifc.wall_builder import build_panel
from gdot_soundwall.ifc.footing_builder import build_footing
from gdot_soundwall.ifc.cap_builder import build_cap
from gdot_soundwall.ifc.pset_builder import (
    attach_post_pset, attach_panel_pset, attach_footing_pset,
    attach_joint_pset, attach_surface_treatment_pset,
    attach_wall_common_pset, attach_wall_quantities,
)
from gdot_soundwall.ifc.spatial_structure import contain_in_facility, aggregate_in_facility
from gdot_soundwall.model.wall_assembly import WallLayout, Bay
from gdot_soundwall.model.joints import Joint
from gdot_soundwall.config import JointType


def build_joint_proxy(
    ctx: IfcProjectContext,
    joint: Joint,
) -> object:
    """Create an IfcBuildingElementProxy for a joint."""
    f = ctx.file
    placement = create_placement(
        ctx,
        joint.easting, joint.northing, joint.ground_elevation,
        bearing=joint.bearing,
    )
    proxy = f.create_entity("IfcBuildingElementProxy",
                            GlobalId=ifcopenshell.guid.new(),
                            OwnerHistory=ctx.owner_history,
                            Name=f"Joint_{joint.joint_type.value}_{joint.bay_index}",
                            ObjectPlacement=placement,
                            PredefinedType="USERDEFINED",
                            ObjectType=f"{joint.joint_type.value.upper()}_JOINT")
    return proxy


def build_all_assemblies(
    ctx: IfcProjectContext,
    layout: WallLayout,
    type_lib: TypeLibrary,
    mat_lib: MaterialLibrary,
) -> List[object]:
    """Build IfcElementAssembly for every bay in the layout.

    Returns list of assembly entities for spatial containment.
    """
    f = ctx.file
    guid = ifcopenshell.guid.new
    assemblies = []
    all_top_level = []  # Elements to contain in facility

    # Track which posts/footings have been built (shared between bays)
    built_posts = {}   # post_index -> IfcColumn
    built_footings = {}  # post_index -> IfcFooting

    for bay in layout.bays:
        assembly_children = []

        # ── Left Post (build if not already built) ────────────────
        if bay.post_left.index not in built_posts:
            ifc_post = build_post(ctx, bay.post_left, type_lib, mat_lib)
            attach_post_pset(ctx, ifc_post, bay.post_left)
            built_posts[bay.post_left.index] = ifc_post
            assembly_children.append(ifc_post)

        # ── Right Post (build for last bay) ───────────────────────
        if bay.post_right.index not in built_posts:
            ifc_post = build_post(ctx, bay.post_right, type_lib, mat_lib)
            attach_post_pset(ctx, ifc_post, bay.post_right)
            built_posts[bay.post_right.index] = ifc_post
            assembly_children.append(ifc_post)

        # ── Panels ────────────────────────────────────────────────
        for panel in bay.panels:
            ifc_wall = build_panel(ctx, panel, type_lib, mat_lib)
            attach_panel_pset(ctx, ifc_wall, panel)
            attach_surface_treatment_pset(ctx, ifc_wall)
            attach_wall_common_pset(ctx, ifc_wall, panel)
            attach_wall_quantities(ctx, ifc_wall, panel)
            assembly_children.append(ifc_wall)

        # ── Footings ──────────────────────────────────────────────
        if bay.footing_left and bay.post_left.index not in built_footings:
            ifc_ftg = build_footing(ctx, bay.footing_left, type_lib, mat_lib)
            attach_footing_pset(ctx, ifc_ftg, bay.footing_left)
            built_footings[bay.post_left.index] = ifc_ftg
            assembly_children.append(ifc_ftg)

        if bay.footing_right and bay.post_right.index not in built_footings:
            ifc_ftg = build_footing(ctx, bay.footing_right, type_lib, mat_lib)
            attach_footing_pset(ctx, ifc_ftg, bay.footing_right)
            built_footings[bay.post_right.index] = ifc_ftg
            assembly_children.append(ifc_ftg)

        # ── Cap ───────────────────────────────────────────────────
        ifc_cap = None
        if bay.cap:
            ifc_cap = build_cap(ctx, bay.cap, mat_lib)
            assembly_children.append(ifc_cap)

        # ── Joints ────────────────────────────────────────────────
        for joint in bay.joints:
            ifc_proxy = build_joint_proxy(ctx, joint)
            attach_joint_pset(ctx, ifc_proxy, joint)
            assembly_children.append(ifc_proxy)

        # ── Create Assembly ───────────────────────────────────────
        mid_station = (bay.post_left.station + bay.post_right.station) / 2.0
        mid_e = (bay.post_left.easting + bay.post_right.easting) / 2.0
        mid_n = (bay.post_left.northing + bay.post_right.northing) / 2.0
        mid_z = min(bay.post_left.ground_elevation, bay.post_right.ground_elevation)

        placement = create_placement(ctx, mid_e, mid_n, mid_z,
                                     bearing=bay.post_left.bearing)

        assembly = f.create_entity("IfcElementAssembly",
                                   GlobalId=guid(),
                                   OwnerHistory=ctx.owner_history,
                                   Name=f"Bay_{bay.index}",
                                   ObjectPlacement=placement,
                                   PredefinedType="USERDEFINED",
                                   ObjectType="SOUNDWALL_PRECAST")

        # Aggregate children into assembly
        if assembly_children:
            f.create_entity("IfcRelAggregates",
                            GlobalId=guid(),
                            OwnerHistory=ctx.owner_history,
                            RelatingObject=assembly,
                            RelatedObjects=assembly_children)

        assemblies.append(assembly)
        all_top_level.append(assembly)

    # Contain all assemblies in the facility
    if all_top_level:
        contain_in_facility(ctx, all_top_level)

    return assemblies
