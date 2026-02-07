"""CORE: Compute all component positions from alignment + parameters.

This is the main layout engine that takes parsed alignment data and
GDOT configuration parameters to produce a complete WallLayout with
all posts, panels, footings, caps, joints, and drainage slots positioned.
"""
from __future__ import annotations

import math
from typing import Optional

from gdot_soundwall import config
from gdot_soundwall.config import WallType, FoundationType, JointType
from gdot_soundwall.landxml.alignment import HorizontalAlignment
from gdot_soundwall.landxml.profile import VerticalProfile
from gdot_soundwall.landxml.surface import TerrainSurface
from gdot_soundwall.geometry.station_solver import StationSolver
from gdot_soundwall.geometry.terrain_sampler import TerrainSampler
from gdot_soundwall.geometry.step_transitions import compute_step_transitions
from gdot_soundwall.model.wall_assembly import WallLayout, Bay
from gdot_soundwall.model.post import SteelPost
from gdot_soundwall.model.panel import PrecastPanel
from gdot_soundwall.model.footing import Footing, make_caisson, make_spread_footing
from gdot_soundwall.model.cap import Cap
from gdot_soundwall.model.joints import Joint
from gdot_soundwall.model.drainage import DrainageSlot
from gdot_soundwall.model.mse import MSESegment


class WallLayoutEngine:
    """Computes complete sound wall layout from alignment data."""

    def __init__(
        self,
        alignment: HorizontalAlignment,
        profile: Optional[VerticalProfile] = None,
        surface: Optional[TerrainSurface] = None,
        wall_type: WallType = WallType.PRECAST,
        wall_height: float = config.DEFAULT_WALL_HEIGHT,
        foundation_type: FoundationType = FoundationType.CAISSON,
        post_spacing: float = config.POST_SPACING_MAX,
        start_station: Optional[float] = None,
        end_station: Optional[float] = None,
        offset: float = 0.0,
    ):
        self.alignment = alignment
        self.profile = profile
        self.surface = surface
        self.wall_type = wall_type
        self.wall_height = wall_height
        self.foundation_type = foundation_type
        self.post_spacing = post_spacing
        self.offset = offset

        self.start_station = start_station or alignment.start_station
        self.end_station = end_station or alignment.end_station

        self.solver = StationSolver(alignment, profile)
        self.sampler = TerrainSampler(surface)

    def compute(self) -> WallLayout:
        """Compute the complete wall layout."""
        layout = WallLayout(
            wall_type=self.wall_type,
            start_station=self.start_station,
            end_station=self.end_station,
            wall_height=self.wall_height,
            foundation_type=self.foundation_type,
        )

        if self.wall_type == WallType.PRECAST:
            self._compute_precast(layout)
        elif self.wall_type == WallType.MSE_COMPOSITE:
            self._compute_mse(layout)

        return layout

    def _compute_precast(self, layout: WallLayout) -> None:
        """Compute layout for precast post-and-panel wall."""
        # Step 1: Determine post stations
        post_stations = self._compute_post_stations()

        # Step 2: Create posts with ground elevations
        for i, station in enumerate(post_stations):
            point = self.solver.solve(station, self.offset)
            ground_elev = self.sampler.sample_at_station(
                self.solver, station, self.offset
            )

            post = SteelPost(
                index=i,
                station=station,
                easting=point.easting,
                northing=point.northing,
                ground_elevation=ground_elev,
                top_elevation=ground_elev + self.wall_height,
                bearing=point.bearing,
                height=self.wall_height,
            )
            layout.posts.append(post)

        # Step 3: Create footings under each post
        for post in layout.posts:
            footing = self._make_footing(post)
            layout.footings.append(footing)

        # Step 4: Create bays with panels
        for i in range(len(layout.posts) - 1):
            left = layout.posts[i]
            right = layout.posts[i + 1]
            bay = self._make_bay(i, left, right, layout)
            layout.bays.append(bay)

        # Step 5: Determine joint locations
        self._compute_joints(layout)

        # Flatten panels, caps, drainage from bays
        for bay in layout.bays:
            layout.panels.extend(bay.panels)
            if bay.cap:
                layout.caps.append(bay.cap)
            layout.drainage_slots.extend(bay.drainage_slots)

    def _compute_post_stations(self) -> list[float]:
        """Compute stations for all posts at regular spacing."""
        stations = []
        total_length = self.end_station - self.start_station
        num_bays = max(1, math.ceil(total_length / self.post_spacing))
        actual_spacing = total_length / num_bays

        for i in range(num_bays + 1):
            sta = self.start_station + i * actual_spacing
            stations.append(sta)

        return stations

    def _make_footing(self, post: SteelPost) -> Footing:
        """Create a footing for a post based on foundation type."""
        if self.foundation_type == FoundationType.CAISSON:
            return make_caisson(
                post_index=post.index,
                station=post.station,
                easting=post.easting,
                northing=post.northing,
                top_elevation=post.ground_elevation,
                bearing=post.bearing,
            )
        else:
            return make_spread_footing(
                post_index=post.index,
                station=post.station,
                easting=post.easting,
                northing=post.northing,
                top_elevation=post.ground_elevation,
                bearing=post.bearing,
            )

    def _make_bay(
        self, index: int, left: SteelPost, right: SteelPost, layout: WallLayout,
    ) -> Bay:
        """Create a bay with stacked panels and a cap."""
        bay = Bay(
            index=index,
            post_left=left,
            post_right=right,
        )

        # Bay geometry
        mid_e = (left.easting + right.easting) / 2.0
        mid_n = (left.northing + right.northing) / 2.0
        bay_width = math.sqrt(
            (right.easting - left.easting) ** 2 +
            (right.northing - left.northing) ** 2
        )

        # Ground and top at this bay
        ground_elev = min(left.ground_elevation, right.ground_elevation)
        top_elev = max(left.top_elevation, right.top_elevation)
        wall_h = top_elev - ground_elev - config.CAP_HEIGHT

        # Number of stacked panels
        num_panels = max(1, math.ceil(wall_h / config.PANEL_HEIGHT))

        bearing = left.bearing  # Use left post bearing for panel orientation

        # Create stacked panels
        for s in range(num_panels):
            bottom_elev = ground_elev + s * config.PANEL_HEIGHT

            # Check if this bay should have drainage at bottom panel
            has_drainage = False
            if s == 0:
                bay_station = (left.station + right.station) / 2.0
                # Drainage slots at regular intervals
                dist_from_start = bay_station - self.start_station
                if abs(dist_from_start % config.DRAINAGE_SLOT_SPACING) < self.post_spacing:
                    has_drainage = True

            panel = PrecastPanel(
                bay_index=index,
                stack_index=s,
                station_start=left.station,
                station_end=right.station,
                easting=mid_e,
                northing=mid_n,
                bottom_elevation=bottom_elev,
                bearing=bearing,
                width=bay_width,
                height=config.PANEL_HEIGHT,
                thickness=config.PANEL_THICKNESS,
                has_drainage_slot=has_drainage,
            )
            bay.panels.append(panel)

            if has_drainage:
                slot = DrainageSlot(
                    panel_bay_index=index,
                    station=(left.station + right.station) / 2.0,
                    easting=mid_e,
                    northing=mid_n,
                    elevation=bottom_elev + config.DRAINAGE_SLOT_HEIGHT / 2.0,
                )
                bay.drainage_slots.append(slot)

        # Cap on top
        cap_bottom = ground_elev + num_panels * config.PANEL_HEIGHT
        bay.cap = Cap(
            bay_index=index,
            station_start=left.station,
            station_end=right.station,
            easting=mid_e,
            northing=mid_n,
            bottom_elevation=cap_bottom,
            bearing=bearing,
            width=bay_width,
        )

        # Assign footings
        if layout.footings:
            bay.footing_left = layout.footings[left.index]
            if right.index < len(layout.footings):
                bay.footing_right = layout.footings[right.index]

        return bay

    def _compute_joints(self, layout: WallLayout) -> None:
        """Compute expansion and contraction joint locations."""
        dist_since_expansion = 0.0
        dist_since_contraction = 0.0

        for i in range(len(layout.posts) - 1):
            left = layout.posts[i]
            right = layout.posts[i + 1]
            bay_length = right.station - left.station

            dist_since_expansion += bay_length
            dist_since_contraction += bay_length

            # Expansion joint check
            if dist_since_expansion >= config.EXPANSION_JOINT_SPACING:
                joint = Joint(
                    joint_type=JointType.EXPANSION,
                    station=right.station,
                    easting=right.easting,
                    northing=right.northing,
                    ground_elevation=right.ground_elevation,
                    top_elevation=right.top_elevation,
                    bearing=right.bearing,
                    bay_index=i,
                )
                layout.joints.append(joint)
                if i < len(layout.bays):
                    layout.bays[i].joints.append(joint)
                dist_since_expansion = 0.0
                dist_since_contraction = 0.0

            # Contraction joint check
            elif dist_since_contraction >= config.CONTRACTION_JOINT_SPACING:
                joint = Joint(
                    joint_type=JointType.CONTRACTION,
                    station=right.station,
                    easting=right.easting,
                    northing=right.northing,
                    ground_elevation=right.ground_elevation,
                    top_elevation=right.top_elevation,
                    bearing=right.bearing,
                    bay_index=i,
                )
                layout.joints.append(joint)
                if i < len(layout.bays):
                    layout.bays[i].joints.append(joint)
                dist_since_contraction = 0.0

    def _compute_mse(self, layout: WallLayout) -> None:
        """Compute layout for MSE wall with noise barrier on top."""
        # MSE walls are laid out as continuous segments
        segment_length = config.EXPANSION_JOINT_SPACING  # Break at expansion joints
        total_length = self.end_station - self.start_station
        num_segments = max(1, math.ceil(total_length / segment_length))
        actual_segment_length = total_length / num_segments

        for i in range(num_segments):
            sta_start = self.start_station + i * actual_segment_length
            sta_end = self.start_station + (i + 1) * actual_segment_length

            pt_start = self.solver.solve(sta_start, self.offset)
            pt_end = self.solver.solve(sta_end, self.offset)

            ground_start = self.sampler.sample_at_station(
                self.solver, sta_start, self.offset
            )
            ground_end = self.sampler.sample_at_station(
                self.solver, sta_end, self.offset
            )

            base_elev = min(ground_start, ground_end)
            mse_height = 3.048  # 10 ft typical MSE height

            segment = MSESegment(
                index=i,
                station_start=sta_start,
                station_end=sta_end,
                easting_start=pt_start.easting,
                northing_start=pt_start.northing,
                easting_end=pt_end.easting,
                northing_end=pt_end.northing,
                base_elevation=base_elev,
                top_elevation=base_elev + mse_height + self.wall_height,
                bearing=pt_start.bearing,
                wall_height=mse_height,
            )
            layout.mse_segments.append(segment)

        # Also compute posts/panels for the noise barrier portion on top of MSE
        self._compute_precast(layout)
