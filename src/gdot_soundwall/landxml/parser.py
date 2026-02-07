"""LandXML ingestion via lxml.

Parses a LandXML file and extracts:
- HorizontalAlignment (CoordGeom elements: Line, Curve, Spiral)
- VerticalProfile (ProfAlign PVIs and vertical curves)
- TerrainSurface (TIN mesh from Surfaces/Surface)

Automatically detects imperial (US Survey Feet) vs metric units and
converts all output values to meters for internal use.
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

# US Survey Foot to meter
US_SURVEY_FT_TO_M = 0.30480060960121924
INTL_FT_TO_M = 0.3048


def _parse_coords(text: str) -> Tuple[float, float]:
    """Parse 'northing easting' or 'northing easting elevation' from LandXML."""
    parts = text.strip().split()
    # LandXML uses northing, easting order
    return float(parts[1]), float(parts[0])  # return easting, northing


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

        # Detect linear units
        self._linear_scale = 1.0  # meters by default
        self._unit_name = "meter"
        self._detect_units()

    def _detect_units(self) -> None:
        """Detect whether the file uses imperial or metric linear units."""
        # Look for <Units><Imperial .../> or <Units><Metric .../>
        units_elem = self._find_first(self.root, "Units")
        if units_elem is None:
            return

        imperial = self._find_first(units_elem, "Imperial")
        if imperial is not None:
            lu = (imperial.get("linearUnit") or "").lower()
            if "ussurveyfoo" in lu or "usfoot" in lu or "ussurvey" in lu:
                self._linear_scale = US_SURVEY_FT_TO_M
                self._unit_name = "USSurveyFoot"
            elif "foot" in lu or "feet" in lu:
                self._linear_scale = INTL_FT_TO_M
                self._unit_name = "foot"
            return

        metric = self._find_first(units_elem, "Metric")
        if metric is not None:
            lu = (metric.get("linearUnit") or "").lower()
            if "meter" in lu or "metre" in lu:
                self._linear_scale = 1.0
                self._unit_name = "meter"

    def _to_m(self, value: float) -> float:
        """Convert a length value from file units to meters."""
        return value * self._linear_scale

    @property
    def is_imperial(self) -> bool:
        return self._linear_scale != 1.0

    def _tag(self, local_name: str) -> str:
        """Return fully qualified tag name."""
        return f"{self.ns}{local_name}"

    def _find(self, parent: etree._Element, path: str) -> list:
        """Find elements supporting both namespaced and plain XML."""
        # Handle ".//X/Y" patterns
        if path.startswith(".//"):
            inner = path[3:]
            parts = inner.split("/")
            qualified = ".//" + "/".join(self._tag(p) for p in parts)
        else:
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

        All coordinates and lengths are converted to meters.
        Bearings (dir attributes) are in radians and kept as-is.
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
        sta_start = self._to_m(float(align_elem.get("staStart", "0")))

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
                se, sn = self._to_m(se), self._to_m(sn)
                ee, en = self._to_m(ee), self._to_m(en)

                length_raw = elem.get("length")
                if length_raw is not None:
                    length = self._to_m(float(length_raw))
                else:
                    length = math.sqrt((ee - se) ** 2 + (en - sn) ** 2)

                # Use dir attribute if present (already in radians)
                dir_attr = elem.get("dir")
                if dir_attr is not None:
                    bearing = float(dir_attr)
                else:
                    bearing = azimuth_from_points(se, sn, ee, en)

                seg = LineSegment(
                    segment_type=None,
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
                se, sn = self._to_m(se), self._to_m(sn)
                ee, en = self._to_m(ee), self._to_m(en)
                ce, cn = self._to_m(ce), self._to_m(cn)

                radius = self._to_m(float(elem.get("radius", "0")))
                length = self._to_m(float(elem.get("length", "0")))
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
                se, sn = self._to_m(se), self._to_m(sn)
                ee, en = self._to_m(ee), self._to_m(en)
                length = self._to_m(float(elem.get("length", "0")))
                radius_start = elem.get("radiusStart", "INF")
                radius_end = elem.get("radiusEnd", "INF")
                rot = elem.get("rot", "cw")

                try:
                    rs = float(radius_start)
                    if rs == 0:
                        rs = float('inf')
                    else:
                        rs = self._to_m(rs)
                except ValueError:
                    rs = float('inf')

                try:
                    re = float(radius_end)
                    if re == 0:
                        re = float('inf')
                    else:
                        re = self._to_m(re)
                except ValueError:
                    re = float('inf')

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
                    start_radius=rs,
                    end_radius=re,
                    start_bearing=start_bearing,
                    is_clockwise=rot.lower() == "cw",
                )
                alignment.segments.append(seg)
                current_station += length

        return alignment

    def parse_profile(self, alignment_name: str = "") -> VerticalProfile:
        """Parse vertical profile (ProfAlign) from alignment.

        Stations and elevations are converted to meters.
        """
        profile = VerticalProfile()

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

        prof_elem = self._find_first(align_elem, "Profile")
        if prof_elem is None:
            return profile

        prof_align = self._find_first(prof_elem, "ProfAlign")
        if prof_align is None:
            return profile

        profile.name = prof_align.get("name", "Profile")

        for elem in prof_align:
            if not isinstance(elem.tag, str):
                continue
            tag = elem.tag.replace(self.ns, "")

            if tag == "PVI":
                parts = elem.text.strip().split()
                station = self._to_m(float(parts[0]))
                elevation = self._to_m(float(parts[1]))
                profile.pvis.append(PVI(station=station, elevation=elevation))

            elif tag in ("CircCurve", "ParaCurve"):
                parts = elem.text.strip().split()
                station = self._to_m(float(parts[0]))
                elevation = self._to_m(float(parts[1]))
                curve_length = self._to_m(float(elem.get("length", "0")))
                profile.pvis.append(PVI(
                    station=station,
                    elevation=elevation,
                    curve_length=curve_length,
                ))

        return profile

    def parse_surface(self, surface_name: str = "") -> TerrainSurface:
        """Parse terrain surface (TIN) from Surfaces element.

        Coordinates are converted to meters.
        """
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

        defn = self._find_first(surf_elem, "Definition")
        if defn is None:
            return surface

        pnts = self._find_first(defn, "Pnts")
        faces = self._find_first(defn, "Faces")

        if pnts is None:
            return surface

        vertices = {}
        for p in pnts:
            if not isinstance(p.tag, str):
                continue
            tag = p.tag.replace(self.ns, "")
            if tag == "P":
                pid = int(p.get("id"))
                parts = p.text.strip().split()
                n = self._to_m(float(parts[0]))
                e = self._to_m(float(parts[1]))
                z = self._to_m(float(parts[2]))
                vertices[pid] = (e, n, z)

        sorted_ids = sorted(vertices.keys())
        id_map = {pid: idx for idx, pid in enumerate(sorted_ids)}
        vert_array = [vertices[pid] for pid in sorted_ids]
        surface.vertices = vert_array

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
