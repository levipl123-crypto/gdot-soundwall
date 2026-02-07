"""Terrain surface TIN mesh and elevation query."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple, Optional

import numpy as np


@dataclass
class TerrainSurface:
    """Triangulated Irregular Network (TIN) terrain surface.

    Stores vertices and triangle indices. Supports elevation queries
    at arbitrary (easting, northing) via barycentric interpolation.
    """
    name: str = ""
    vertices: np.ndarray = field(default_factory=lambda: np.empty((0, 3)))
    triangles: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=int))

    def __post_init__(self):
        if isinstance(self.vertices, list):
            self.vertices = np.array(self.vertices, dtype=float)
        if isinstance(self.triangles, list):
            self.triangles = np.array(self.triangles, dtype=int)

    @property
    def num_vertices(self) -> int:
        return len(self.vertices)

    @property
    def num_triangles(self) -> int:
        return len(self.triangles)

    def elevation_at(self, easting: float, northing: float) -> Optional[float]:
        """Query ground elevation at a point via TIN interpolation.

        Uses barycentric coordinates to find which triangle contains the
        query point and interpolate the elevation.

        Returns None if the point is outside the TIN.
        """
        if len(self.triangles) == 0 or len(self.vertices) == 0:
            return None

        for tri_idx in range(len(self.triangles)):
            i0, i1, i2 = self.triangles[tri_idx]
            v0 = self.vertices[i0]
            v1 = self.vertices[i1]
            v2 = self.vertices[i2]

            elev = self._point_in_triangle(
                easting, northing,
                v0[0], v0[1], v0[2],
                v1[0], v1[1], v1[2],
                v2[0], v2[1], v2[2],
            )
            if elev is not None:
                return elev

        return None

    @staticmethod
    def _point_in_triangle(
        px: float, py: float,
        x0: float, y0: float, z0: float,
        x1: float, y1: float, z1: float,
        x2: float, y2: float, z2: float,
    ) -> Optional[float]:
        """Check if point (px,py) is in triangle and return interpolated elevation."""
        # Compute barycentric coordinates
        denom = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(denom) < 1e-12:
            return None

        lambda0 = ((y1 - y2) * (px - x2) + (x2 - x1) * (py - y2)) / denom
        lambda1 = ((y2 - y0) * (px - x2) + (x0 - x2) * (py - y2)) / denom
        lambda2 = 1.0 - lambda0 - lambda1

        tol = -1e-6
        if lambda0 >= tol and lambda1 >= tol and lambda2 >= tol:
            return lambda0 * z0 + lambda1 * z1 + lambda2 * z2

        return None

    def bounds(self) -> Tuple[float, float, float, float]:
        """Return (min_e, min_n, max_e, max_n) bounding box."""
        if len(self.vertices) == 0:
            return (0.0, 0.0, 0.0, 0.0)
        return (
            float(self.vertices[:, 0].min()),
            float(self.vertices[:, 1].min()),
            float(self.vertices[:, 0].max()),
            float(self.vertices[:, 1].max()),
        )
