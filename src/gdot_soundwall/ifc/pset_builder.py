"""GDOT-specific IfcPropertySet definitions.

Creates and attaches property sets to IFC elements per GDOT sound wall standards.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import ifcopenshell.guid

from gdot_soundwall import config
from gdot_soundwall.ifc.project_setup import IfcProjectContext
from gdot_soundwall.model.wall_assembly import WallLayout, Bay
from gdot_soundwall.model.post import SteelPost
from gdot_soundwall.model.panel import PrecastPanel
from gdot_soundwall.model.footing import Footing
from gdot_soundwall.model.joints import Joint
from gdot_soundwall.model.mse import MSESegment


def _make_value(f, value: Any):
    """Create an appropriate IfcValue for a property."""
    if isinstance(value, bool):
        return f.create_entity("IfcBoolean", value)
    elif isinstance(value, int):
        return f.create_entity("IfcInteger", value)
    elif isinstance(value, float):
        return f.create_entity("IfcReal", value)
    elif isinstance(value, str):
        return f.create_entity("IfcLabel", value)
    return f.create_entity("IfcLabel", str(value))


def _create_pset(
    ctx: IfcProjectContext,
    name: str,
    properties: Dict[str, Any],
    related_objects: list,
) -> object:
    """Create an IfcPropertySet and attach it to objects."""
    f = ctx.file
    guid = ifcopenshell.guid.new

    prop_list = []
    for prop_name, prop_value in properties.items():
        if prop_value is not None:
            prop = f.create_entity("IfcPropertySingleValue",
                                   Name=prop_name,
                                   NominalValue=_make_value(f, prop_value))
            prop_list.append(prop)

    if not prop_list:
        return None

    pset = f.create_entity("IfcPropertySet",
                           GlobalId=guid(),
                           OwnerHistory=ctx.owner_history,
                           Name=name,
                           HasProperties=prop_list)

    f.create_entity("IfcRelDefinesByProperties",
                    GlobalId=guid(),
                    OwnerHistory=ctx.owner_history,
                    RelatedObjects=related_objects,
                    RelatingPropertyDefinition=pset)

    return pset


def attach_general_pset(
    ctx: IfcProjectContext,
    assembly,
    layout: WallLayout,
    project_number: str = "",
    route: str = "",
) -> None:
    """Attach GDOT_SoundWall_General property set to an assembly."""
    _create_pset(ctx, "GDOT_SoundWall_General", {
        "WallType": layout.wall_type.value,
        "StartStation": layout.start_station,
        "EndStation": layout.end_station,
        "WallHeight": layout.wall_height,
        "TotalLength": layout.total_length,
        "NumberOfBays": layout.num_bays,
        "FoundationType": layout.foundation_type.value,
        "ProjectNumber": project_number,
        "Route": route,
    }, [assembly])


def attach_post_pset(
    ctx: IfcProjectContext,
    ifc_column,
    post: SteelPost,
) -> None:
    """Attach GDOT_SoundWall_Post property set to an IfcColumn."""
    _create_pset(ctx, "GDOT_SoundWall_Post", {
        "Station": post.station,
        "PostIndex": post.index,
        "SteelGrade": config.POST_STEEL_GRADE,
        "SectionDesignation": post.section,
        "Galvanized": config.POST_GALVANIZED,
        "Height": post.height,
        "EmbedDepth": config.POST_EMBED_FROM_BOTTOM,
        "GroundElevation": post.ground_elevation,
        "TopElevation": post.top_elevation,
    }, [ifc_column])


def attach_panel_pset(
    ctx: IfcProjectContext,
    ifc_wall,
    panel: PrecastPanel,
) -> None:
    """Attach GDOT_SoundWall_Panel property set to an IfcWall."""
    _create_pset(ctx, "GDOT_SoundWall_Panel", {
        "BayIndex": panel.bay_index,
        "StackIndex": panel.stack_index,
        "MaterialType": config.PANEL_MATERIAL,
        "HasDrainageSlot": panel.has_drainage_slot,
        "Width": panel.width,
        "Height": panel.height,
        "Thickness": panel.thickness,
    }, [ifc_wall])


def attach_footing_pset(
    ctx: IfcProjectContext,
    ifc_footing,
    footing: Footing,
) -> None:
    """Attach GDOT_SoundWall_Footing property set to an IfcFooting."""
    props = {
        "FoundationType": footing.foundation_type.value,
        "ReinforcementCover": config.REBAR_COVER_FOOTING,
        "Depth": footing.depth,
        "TopElevation": footing.top_elevation,
        "BottomElevation": footing.bottom_elevation,
    }
    if footing.diameter > 0:
        props["Diameter"] = footing.diameter
    if footing.width > 0:
        props["Width"] = footing.width
    if footing.length > 0:
        props["Length"] = footing.length

    _create_pset(ctx, "GDOT_SoundWall_Footing", props, [ifc_footing])


def attach_joint_pset(
    ctx: IfcProjectContext,
    ifc_proxy,
    joint: Joint,
) -> None:
    """Attach GDOT_SoundWall_Joint property set."""
    _create_pset(ctx, "GDOT_SoundWall_Joint", {
        "JointType": joint.joint_type.value,
        "Station": joint.station,
        "GapWidth": joint.gap_width,
        "FillerMaterial": joint.filler_material,
    }, [ifc_proxy])


def attach_mse_pset(
    ctx: IfcProjectContext,
    ifc_element,
    segment: MSESegment,
) -> None:
    """Attach GDOT_SoundWall_MSE property set."""
    _create_pset(ctx, "GDOT_SoundWall_MSE", {
        "CompactionPercent": config.MSE_COMPACTION_PERCENT,
        "TrafficBarrierType": "Traffic Barrier H",
        "CopingType": "Cast-in-place Coping B",
        "WallHeight": segment.wall_height,
        "BaseWidth": segment.base_width,
        "TopWidth": segment.top_width,
    }, [ifc_element])


def attach_surface_treatment_pset(
    ctx: IfcProjectContext,
    ifc_wall,
) -> None:
    """Attach GDOT_SurfaceTreatment property set to a wall panel."""
    _create_pset(ctx, "GDOT_SurfaceTreatment", {
        "GraffitiProofCoating": config.GRAFFITI_PROOF_COATING,
        "CoatingSpec": "Per GDOT Section 838",
    }, [ifc_wall])


def attach_wall_common_pset(
    ctx: IfcProjectContext,
    ifc_wall,
    panel: PrecastPanel,
) -> None:
    """Attach standard Pset_WallCommon."""
    _create_pset(ctx, "Pset_WallCommon", {
        "IsExternal": True,
        "LoadBearing": False,
    }, [ifc_wall])


def attach_wall_quantities(
    ctx: IfcProjectContext,
    ifc_wall,
    panel: PrecastPanel,
) -> None:
    """Attach Qto_WallBaseQuantities."""
    f = ctx.file
    guid = ifcopenshell.guid.new

    quantities = [
        f.create_entity("IfcQuantityLength", Name="Length",
                        LengthValue=panel.width),
        f.create_entity("IfcQuantityLength", Name="Height",
                        LengthValue=panel.height),
        f.create_entity("IfcQuantityLength", Name="Width",
                        LengthValue=panel.thickness),
        f.create_entity("IfcQuantityArea", Name="GrossFootprintArea",
                        AreaValue=panel.width * panel.thickness),
        f.create_entity("IfcQuantityArea", Name="GrossSideArea",
                        AreaValue=panel.width * panel.height),
        f.create_entity("IfcQuantityVolume", Name="GrossVolume",
                        VolumeValue=panel.width * panel.height * panel.thickness),
    ]

    qto = f.create_entity("IfcElementQuantity",
                          GlobalId=guid(),
                          OwnerHistory=ctx.owner_history,
                          Name="Qto_WallBaseQuantities",
                          Quantities=quantities)

    f.create_entity("IfcRelDefinesByProperties",
                    GlobalId=guid(),
                    OwnerHistory=ctx.owner_history,
                    RelatedObjects=[ifc_wall],
                    RelatingPropertyDefinition=qto)
