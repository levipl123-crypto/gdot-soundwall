"""Build IfcColumn entities for steel posts."""
from __future__ import annotations

import ifcopenshell.guid

from gdot_soundwall.ifc.project_setup import IfcProjectContext
from gdot_soundwall.ifc.geometry_builder import (
    create_placement, create_i_shape_profile, create_extruded_solid,
    create_shape_representation, create_product_shape,
)
from gdot_soundwall.ifc.type_library import TypeLibrary
from gdot_soundwall.ifc.material_builder import MaterialLibrary, assign_material
from gdot_soundwall.model.post import SteelPost
from gdot_soundwall.model.materials import STEEL_AASHTO_M270_GR36


def build_post(
    ctx: IfcProjectContext,
    post: SteelPost,
    type_lib: TypeLibrary,
    mat_lib: MaterialLibrary,
) -> object:
    """Create an IfcColumn for a steel post.

    Uses per-instance geometry (extruded to actual height) since posts
    may have varying heights on sloped terrain.
    """
    f = ctx.file
    guid = ifcopenshell.guid.new

    # Placement at post base (ground level)
    placement = create_placement(
        ctx,
        post.easting,
        post.northing,
        post.ground_elevation,
        bearing=post.bearing,
    )

    # Create geometry - extrude I-shape to post height
    profile = create_i_shape_profile(
        ctx, post.section,
        width=post.flange_width,
        depth=post.depth,
        web_thickness=post.web_thickness,
        flange_thickness=post.flange_thickness,
    )
    solid = create_extruded_solid(ctx, profile, depth=post.height)
    body_rep = create_shape_representation(ctx, [solid])
    shape = create_product_shape(ctx, [body_rep])

    # Create IfcColumn
    column = f.create_entity("IfcColumn",
                             GlobalId=guid(),
                             OwnerHistory=ctx.owner_history,
                             Name=f"Post_{post.index}",
                             ObjectPlacement=placement,
                             Representation=shape,
                             PredefinedType="USERDEFINED",
                             ObjectType="SOUNDWALL_POST")

    # Assign type
    if type_lib.post_type:
        f.create_entity("IfcRelDefinesByType",
                        GlobalId=guid(),
                        OwnerHistory=ctx.owner_history,
                        RelatedObjects=[column],
                        RelatingType=type_lib.post_type)

    # Assign material
    steel_mat = mat_lib.materials.get(STEEL_AASHTO_M270_GR36.name)
    if steel_mat:
        assign_material(ctx, column, steel_mat)

    return column
