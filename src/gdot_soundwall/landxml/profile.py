"""Vertical profile data structures and computation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from gdot_soundwall.utils.math_helpers import (
    interpolate_linear, parabolic_curve_elevation,
)


@dataclass
class PVI:
    """Point of Vertical Intersection."""
    station: float
    elevation: float
    curve_length: float = 0.0     # Length of vertical curve through this PVI

    @property
    def has_curve(self) -> bool:
        return self.curve_length > 0.0

    @property
    def bvc_station(self) -> float:
        """Beginning of vertical curve station."""
        return self.station - self.curve_length / 2.0

    @property
    def evc_station(self) -> float:
        """End of vertical curve station."""
        return self.station + self.curve_length / 2.0


@dataclass
class VerticalProfile:
    """Vertical profile defined by a series of PVIs."""
    name: str = ""
    pvis: List[PVI] = field(default_factory=list)

    @property
    def start_station(self) -> float:
        if not self.pvis:
            return 0.0
        return self.pvis[0].station

    @property
    def end_station(self) -> float:
        if not self.pvis:
            return 0.0
        return self.pvis[-1].station

    def _grade_between(self, pvi1: PVI, pvi2: PVI) -> float:
        """Compute grade (slope) between two PVIs."""
        ds = pvi2.station - pvi1.station
        if abs(ds) < 1e-10:
            return 0.0
        return (pvi2.elevation - pvi1.elevation) / ds

    def elevation_at_station(self, station: float) -> float:
        """Compute profile elevation at a given station.

        Handles tangent sections and parabolic vertical curves.
        """
        if not self.pvis:
            return 0.0

        if len(self.pvis) == 1:
            return self.pvis[0].elevation

        # Check if station is on a vertical curve
        for i, pvi in enumerate(self.pvis):
            if pvi.has_curve:
                if pvi.bvc_station <= station <= pvi.evc_station:
                    # Determine incoming and outgoing grades
                    if i > 0:
                        grade_in = self._grade_between(self.pvis[i - 1], pvi)
                    else:
                        grade_in = 0.0
                    if i < len(self.pvis) - 1:
                        grade_out = self._grade_between(pvi, self.pvis[i + 1])
                    else:
                        grade_out = 0.0

                    return parabolic_curve_elevation(
                        station, pvi.station, pvi.elevation,
                        grade_in, grade_out, pvi.curve_length,
                    )

        # Station is on a tangent section - interpolate between PVIs
        # Find the two PVIs that bracket this station
        for i in range(len(self.pvis) - 1):
            pvi1 = self.pvis[i]
            pvi2 = self.pvis[i + 1]

            # Adjust boundaries for curves
            sta1 = pvi1.evc_station if pvi1.has_curve else pvi1.station
            sta2 = pvi2.bvc_station if pvi2.has_curve else pvi2.station

            if sta1 <= station <= sta2:
                # Elevation at sta1
                if pvi1.has_curve:
                    elev1 = self.elevation_at_station(sta1 - 0.001) + self._grade_between(pvi1, pvi2) * 0.001
                    # Actually just use the grade between PVIs
                    grade = self._grade_between(pvi1, pvi2)
                    elev_at_pvi1_evc = pvi1.elevation + self._grade_between(
                        self.pvis[i - 1] if i > 0 else pvi1, pvi1
                    ) * (pvi1.curve_length / 2.0) if pvi1.has_curve else pvi1.elevation
                else:
                    elev_at_pvi1_evc = pvi1.elevation

                grade = self._grade_between(pvi1, pvi2)
                return pvi1.elevation + grade * (station - pvi1.station)

        # Extrapolate
        if station <= self.pvis[0].station:
            if len(self.pvis) >= 2:
                grade = self._grade_between(self.pvis[0], self.pvis[1])
                return self.pvis[0].elevation + grade * (station - self.pvis[0].station)
            return self.pvis[0].elevation

        if station >= self.pvis[-1].station:
            if len(self.pvis) >= 2:
                grade = self._grade_between(self.pvis[-2], self.pvis[-1])
                return self.pvis[-1].elevation + grade * (station - self.pvis[-1].station)
            return self.pvis[-1].elevation

        return 0.0
