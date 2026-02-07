"""Height change step-down logic for sound walls on slopes."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List


@dataclass
class StepTransition:
    """A height step transition between bays."""
    station: float
    bay_index: int
    height_change: float          # Positive = step up, negative = step down
    num_panels_before: int
    num_panels_after: int


def compute_step_transitions(
    ground_elevations: List[float],
    stations: List[float],
    wall_height: float,
    panel_height: float,
) -> List[StepTransition]:
    """Determine where the wall needs to step up or down.

    When the ground elevation changes enough between adjacent posts that
    the number of stacked panels needs to change, a step transition occurs.

    Args:
        ground_elevations: Ground elevation at each post.
        stations: Station at each post.
        wall_height: Desired wall height above ground.
        panel_height: Height of a single panel.

    Returns:
        List of StepTransition objects.
    """
    if len(ground_elevations) < 2:
        return []

    transitions = []

    for i in range(1, len(ground_elevations)):
        elev_prev = ground_elevations[i - 1]
        elev_curr = ground_elevations[i]

        # Number of panels needed at each location
        n_prev = max(1, math.ceil(wall_height / panel_height))
        n_curr = max(1, math.ceil(wall_height / panel_height))

        # If ground drops significantly, we may need more panels
        ground_diff = elev_curr - elev_prev
        if abs(ground_diff) > panel_height * 0.5:
            # Compute effective height needed
            if ground_diff < 0:
                # Ground drops: need more panels on the lower side
                effective_height = wall_height + abs(ground_diff)
                n_curr = max(1, math.ceil(effective_height / panel_height))
            else:
                # Ground rises: may need fewer panels
                effective_height = wall_height - abs(ground_diff)
                n_curr = max(1, math.ceil(effective_height / panel_height))

            if n_curr != n_prev:
                transitions.append(StepTransition(
                    station=stations[i],
                    bay_index=i - 1,
                    height_change=ground_diff,
                    num_panels_before=n_prev,
                    num_panels_after=n_curr,
                ))

    return transitions
