"""Build IfcFooting / IfcCaissonFoundation entities."""
from __future__ import annotations

import ifcopenshell.guid

from gdot_soundwall.config import FoundationType
from gdot_soundwall.ifc.project_setup import IfcProjectContext
from gdot_soundwall.ifc.geometry_builder import (
    create_placement, create_circle_profile, create_rectangle_profile,
    create_extruded_solid, create_shape_representation, create_product_shape,
)
from gdot_soundwall.ifc.type_library import TypeLibrary
from gdot_soundwall.ifc.material_builder import MaterialLibrary, assign_material
from gdot_soundwall.model.footing import Footing
from gdot_soundwall.model.materials import REINFORCED_CONCRETE


def build_footing(
    ctx: IfcProjectContext,
    footing: Footing,
    type_lib: TypeLibrary,
    mat_lib: MaterialLibrary,
) -> object:
    """Create an IfcFooting or IfcCaissonFoundation entity."""
    f = ctx.file
    guid = ifcopenshell.guid.new

    # Placement at footing top (ground level), extruded downward
    placement = create_placement(
        ctx,
        footing.easting,
        footing.northing,
        footing.top_elevation - footing.depth,  # Place at bottom, extrude up
        bearing=footing.bearing,
    )

    # Create geometry based on foundation type
    if footing.foundation_type == FoundationType.CAISSON:
        profile = create_circle_profile(
            ctx, "Caisson_Profile",
            radius=footing.diameter / 2.0,
        )
        solid = create_extruded_solid(ctx, profile, depth=footing.depth)
        predefined = "CAISSON_FOUNDATION"
        rel_type = type_lib.caisson_type

    elif footing.foundation_type == FoundationType.SPREAD_FOOTING:
        profile = create_rectangle_profile(
            ctx, "SpreadFooting_Profile",
            x_dim=footing.length,
            y_dim=footing.width,
        )
        solid = create_extruded_solid(ctx, profile, depth=footing.depth)
        predefined = "PAD_FOOTING"
        rel_type = type_lib.spread_footing_type

    else:  # CONTINUOUS_FOOTING
        profile = create_rectangle_profile(
            ctx, "ContinuousFooting_Profile",
            x_dim=footing.length,
            y_dim=footing.width,
        )
        solid = create_extruded_solid(ctx, profile, depth=footing.depth)
        predefined = "STRIP_FOOTING"
        rel_type = None

    body_rep = create_shape_representation(ctx, [solid])
    shape = create_product_shape(ctx, [body_rep])

    # Use IfcCaissonFoundation for caissons, IfcFooting for others
    if footing.foundation_type == FoundationType.CAISSON:
        entity = f.create_entity("IfcCaissonFoundation",
                                 GlobalId=guid(),
                                 OwnerHistory=ctx.owner_history,
                                 Name=f"Caisson_{footing.post_index}",
                                 ObjectPlacement=placement,
                                 Representation=shape,
                                 PredefinedType="WELL")
    else:
        entity = f.create_entity("IfcFooting",
                                 GlobalId=guid(),
                                 OwnerHistory=ctx.owner_history,
                                 Name=f"Footing_{footing.post_index}",
                                 ObjectPlacement=placement,
                                 Representation=shape,
                                 PredefinedType=predefined)

    # Assign type
    if rel_type:
        f.create_entity("IfcRelDefinesByType",
                        GlobalId=guid(),
                        OwnerHistory=ctx.owner_history,
                        RelatedObjects=[entity],
                        RelatingType=rel_type)

    # Assign material
    rc_mat = mat_lib.materials.get(REINFORCED_CONCRETE.name)
    if rc_mat:
        assign_material(ctx, entity, rc_mat)

    return entity
