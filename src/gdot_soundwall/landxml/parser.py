"""LandXML ingestion via lxml.

Parses a LandXML file and extracts:
- HorizontalAlignment (CoordGeom elements: Line, Curve, Spiral)
- VerticalProfile (ProfAlign PVIs and vertical curves)
- TerrainSurface (TIN mesh from Surfaces/Surface)
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Tuple, Optional

from lxml import etree

from gdot_soundwall.landxml.alignment import (
    HorizontalAlignment, LineSegment, ArcSegment, SpiralSegment,
)
from gdot_soundwall.landxml.profile import VerticalProfile, PVI
from gdot_soundwall.landxml.surface import TerrainSurface
from gdot_soundwall.utils.math_helpers import azimuth_from_points


# LandXML namespaces
LANDXML_NS = {
    "lx": "http://www.landxml.org/schema/LandXML-1.2",
    "lx11": "http://www.landxml.org/schema/LandXML-1.1",
}


def _find_with_ns(root: etree._Element, xpath_parts: str) -> list:
    """Try finding elements with and without namespace."""
    # Try with LandXML 1.2 namespace
    try:
        result = root.xpath(xpath_parts, namespaces=LANDXML_NS)
        if result:
            return result
    except Exception:
        pass

    # Try without namespace (common in practice)
    # Strip namespace prefixes
    plain = xpath_parts.replace("lx:", "")
    try:
        result = root.xpath(plain)
        if result:
            return result
    except Exception:
        pass

    return []


def _parse_coords(text: str) -> Tuple[float, float]:
    """Parse 'northing easting' or 'northing easting elevation' from LandXML."""
    parts = text.strip().split()
    # LandXML uses northing, easting order
    return float(parts[1]), float(parts[0])  # return easting, northing


def _parse_coords_3d(text: str) -> Tuple[float, float, float]:
    """Parse 'northing easting elevation' from LandXML."""
    parts = text.strip().split()
    return float(parts[1]), float(parts[0]), float(parts[2]) if len(parts) > 2 else 0.0


class LandXMLParser:
    """Parser for LandXML alignment files."""

    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self.tree = etree.parse(str(self.filepath))
        self.root = self.tree.getroot()
        # Detect namespace
        self.ns = ""
        root_tag = self.root.tag
        if "{" in root_tag:
            self.ns = root_tag.split("}")[0] + "}"

    def _tag(self, local_name: str) -> str:
        """Return fully qualified tag name."""
        return f"{self.ns}{local_name}"

    def _find(self, parent: etree._Element, path: str) -> list:
        """Find elements supporting both namespaced and plain XML."""
        parts = path.split("/")
        qualified = "/".join(self._tag(p) for p in parts)
        result = parent.findall(qualified)
        if not result:
            result = parent.findall(path)
        return result

    def _find_first(self, parent: etree._Element, path: str) -> Optional[etree._Element]:
        """Find first matching element."""
        results = self._find(parent, path)
        return results[0] if results else None

    def parse_alignment(self, alignment_name: str = "") -> HorizontalAlignment:
        """Parse horizontal alignment from CoordGeom elements.

        Args:
            alignment_name: Specific alignment name to find. If empty, uses first.
        """
        alignment = HorizontalAlignment()

        # Find Alignment element
        alignments = self._find(self.root, ".//Alignments/Alignment")
        if not alignments:
            alignments = self._find(self.root, "Alignments/Alignment")
        if not alignments:
            raise ValueError("No Alignment element found in LandXML")

        align_elem = alignments[0]
        if alignment_name:
            for a in alignments:
                if a.get("name") == alignment_name:
                    align_elem = a
                    break

        alignment.name = align_elem.get("name", "Alignment")
        sta_start = float(align_elem.get("staStart", "0"))

        # Parse CoordGeom
        coord_geom = self._find_first(align_elem, "CoordGeom")
        if coord_geom is None:
            raise ValueError("No CoordGeom found in Alignment")

        current_station = sta_start

        for elem in coord_geom:
            if not isinstance(elem.tag, str):
                continue  # Skip comments/PIs
            tag = elem.tag.replace(self.ns, "")

            if tag == "Line":
                start_elem = self._find_first(elem, "Start")
                end_elem = self._find_first(elem, "End")
                if start_elem is None or end_elem is None:
                    continue

                se, sn = _parse_coords(start_elem.text)
                ee, en = _parse_coords(end_elem.text)
                length = float(elem.get("length", str(
                    math.sqrt((ee - se) ** 2 + (en - sn) ** 2)
                )))

                bearing = azimuth_from_points(se, sn, ee, en)
                seg = LineSegment(
                    segment_type=None,  # Set in __post_init__
                    start_station=current_station,
                    end_station=current_station + length,
                    start_easting=se,
                    start_northing=sn,
                    end_easting=ee,
                    end_northing=en,
                    bearing=bearing,
                )
                alignment.segments.append(seg)
                current_station += length

            elif tag == "Curve":
                start_elem = self._find_first(elem, "Start")
                end_elem = self._find_first(elem, "End")
                center_elem = self._find_first(elem, "Center")
                if start_elem is None or end_elem is None or center_elem is None:
                    continue

                se, sn = _parse_coords(start_elem.text)
                ee, en = _parse_coords(end_elem.text)
                ce, cn = _parse_coords(center_elem.text)

                radius = float(elem.get("radius", "0"))
                length = float(elem.get("length", "0"))
                rot = elem.get("rot", "cw")
                is_cw = rot.lower() == "cw"

                # Compute start and end bearings
                start_radial = math.atan2(se - ce, sn - cn)
                end_radial = math.atan2(ee - ce, en - cn)

                if is_cw:
                    start_bearing = start_radial + math.pi / 2
                    end_bearing = end_radial + math.pi / 2
                else:
                    start_bearing = start_radial - math.pi / 2
                    end_bearing = end_radial - math.pi / 2

                seg = ArcSegment(
                    segment_type=None,
                    start_station=current_station,
                    end_station=current_station + length,
                    start_easting=se,
                    start_northing=sn,
                    end_easting=ee,
                    end_northing=en,
                    radius=radius,
                    center_easting=ce,
                    center_northing=cn,
                    is_clockwise=is_cw,
                    start_bearing=start_bearing,
                    end_bearing=end_bearing,
                )
                alignment.segments.append(seg)
                current_station += length

            elif tag == "Spiral":
                start_elem = self._find_first(elem, "Start")
                end_elem = self._find_first(elem, "End")
                if start_elem is None or end_elem is None:
                    continue

                se, sn = _parse_coords(start_elem.text)
                ee, en = _parse_coords(end_elem.text)
                length = float(elem.get("length", "0"))
                radius_start = float(elem.get("radiusStart", "INF"))
                radius_end = float(elem.get("radiusEnd", "INF"))
                rot = elem.get("rot", "cw")

                if radius_start == 0 or str(radius_start).upper() == "INF":
                    radius_start = float('inf')
                if radius_end == 0 or str(radius_end).upper() == "INF":
                    radius_end = float('inf')

                # Compute start bearing from previous segment or from coords
                start_bearing = azimuth_from_points(se, sn, ee, en)
                if alignment.segments:
                    prev = alignment.segments[-1]
                    _, _, start_bearing = prev.point_at_station(prev.end_station)

                seg = SpiralSegment(
                    segment_type=None,
                    start_station=current_station,
                    end_station=current_station + length,
                    start_easting=se,
                    start_northing=sn,
                    end_easting=ee,
                    end_northing=en,
                    start_radius=radius_start,
                    end_radius=radius_end,
                    start_bearing=start_bearing,
                    is_clockwise=rot.lower() == "cw",
                )
                alignment.segments.append(seg)
                current_station += length

        return alignment

    def parse_profile(self, alignment_name: str = "") -> VerticalProfile:
        """Parse vertical profile (ProfAlign) from alignment."""
        profile = VerticalProfile()

        # Find Profile under Alignment
        alignments = self._find(self.root, ".//Alignments/Alignment")
        if not alignments:
            alignments = self._find(self.root, "Alignments/Alignment")
        if not alignments:
            return profile

        align_elem = alignments[0]
        if alignment_name:
            for a in alignments:
                if a.get("name") == alignment_name:
                    align_elem = a
                    break

        # Find Profile -> ProfAlign
        prof_elem = self._find_first(align_elem, "Profile")
        if prof_elem is None:
            return profile

        prof_align = self._find_first(prof_elem, "ProfAlign")
        if prof_align is None:
            return profile

        profile.name = prof_align.get("name", "Profile")

        # Parse PVI elements
        for elem in prof_align:
            if not isinstance(elem.tag, str):
                continue
            tag = elem.tag.replace(self.ns, "")

            if tag == "PVI":
                parts = elem.text.strip().split()
                station = float(parts[0])
                elevation = float(parts[1])
                profile.pvis.append(PVI(station=station, elevation=elevation))

            elif tag in ("CircCurve", "ParaCurve"):
                parts = elem.text.strip().split()
                station = float(parts[0])
                elevation = float(parts[1])
                curve_length = float(elem.get("length", "0"))
                profile.pvis.append(PVI(
                    station=station,
                    elevation=elevation,
                    curve_length=curve_length,
                ))

        return profile

    def parse_surface(self, surface_name: str = "") -> TerrainSurface:
        """Parse terrain surface (TIN) from Surfaces element."""
        surface = TerrainSurface()

        surfaces = self._find(self.root, ".//Surfaces/Surface")
        if not surfaces:
            surfaces = self._find(self.root, "Surfaces/Surface")
        if not surfaces:
            return surface

        surf_elem = surfaces[0]
        if surface_name:
            for s in surfaces:
                if s.get("name") == surface_name:
                    surf_elem = s
                    break

        surface.name = surf_elem.get("name", "Surface")

        # Parse Definition/Pnts/P elements
        defn = self._find_first(surf_elem, "Definition")
        if defn is None:
            return surface

        pnts = self._find_first(defn, "Pnts")
        faces = self._find_first(defn, "Faces")

        if pnts is None:
            return surface

        # Build vertex array indexed by point ID
        vertices = {}
        for p in pnts:
            if not isinstance(p.tag, str):
                continue
            tag = p.tag.replace(self.ns, "")
            if tag == "P":
                pid = int(p.get("id"))
                parts = p.text.strip().split()
                # LandXML: northing easting elevation
                n, e, z = float(parts[0]), float(parts[1]), float(parts[2])
                vertices[pid] = (e, n, z)

        # Reindex vertices to 0-based array
        sorted_ids = sorted(vertices.keys())
        id_map = {pid: idx for idx, pid in enumerate(sorted_ids)}
        vert_array = [vertices[pid] for pid in sorted_ids]
        surface.vertices = vert_array

        # Parse Faces/F elements
        if faces is not None:
            tri_list = []
            for f in faces:
                if not isinstance(f.tag, str):
                    continue
                tag = f.tag.replace(self.ns, "")
                if tag == "F":
                    parts = f.text.strip().split()
                    i0 = id_map[int(parts[0])]
                    i1 = id_map[int(parts[1])]
                    i2 = id_map[int(parts[2])]
                    tri_list.append((i0, i1, i2))
            surface.triangles = tri_list

        return surface
