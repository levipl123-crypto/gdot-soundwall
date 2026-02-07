"""IfcRelContainedInSpatialStructure management.

Handles spatial containment of elements within the facility.
"""
from __future__ import annotations

from typing import List

import ifcopenshell.guid

from gdot_soundwall.ifc.project_setup import IfcProjectContext


def contain_in_facility(
    ctx: IfcProjectContext,
    elements: List[object],
) -> object:
    """Create IfcRelContainedInSpatialStructure to place elements in facility."""
    f = ctx.file
    return f.create_entity("IfcRelContainedInSpatialStructure",
                           GlobalId=ifcopenshell.guid.new(),
                           OwnerHistory=ctx.owner_history,
                           Name="FacilityContainer",
                           RelatedElements=elements,
                           RelatingStructure=ctx.facility)


def aggregate_in_facility(
    ctx: IfcProjectContext,
    elements: List[object],
) -> object:
    """Create IfcRelAggregates to decompose facility into assemblies."""
    f = ctx.file
    return f.create_entity("IfcRelAggregates",
                           GlobalId=ifcopenshell.guid.new(),
                           OwnerHistory=ctx.owner_history,
                           RelatingObject=ctx.facility,
                           RelatedObjects=elements)
