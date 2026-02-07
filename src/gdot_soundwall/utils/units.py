"""Imperial/metric conversion helpers."""
import math


# Length conversions
def ft_to_m(feet: float) -> float:
    """Convert feet to meters."""
    return feet * 0.3048


def m_to_ft(meters: float) -> float:
    """Convert meters to feet."""
    return meters / 0.3048


def in_to_m(inches: float) -> float:
    """Convert inches to meters."""
    return inches * 0.0254


def m_to_in(meters: float) -> float:
    """Convert meters to inches."""
    return meters / 0.0254


# Angle conversions
def deg_to_rad(degrees: float) -> float:
    """Convert degrees to radians."""
    return math.radians(degrees)


def rad_to_deg(radians: float) -> float:
    """Convert radians to degrees."""
    return math.degrees(radians)


# Station formatting
def station_to_str(station_m: float, imperial: bool = True) -> str:
    """Format a station value as a string.

    Args:
        station_m: Station in meters.
        imperial: If True, format as XX+YY.YY (feet). Otherwise metric.
    """
    if imperial:
        sta_ft = m_to_ft(station_m)
        hundreds = int(sta_ft // 100)
        remainder = sta_ft % 100
        return f"{hundreds}+{remainder:05.2f}"
    else:
        hundreds = int(station_m // 1000)
        remainder = station_m % 1000
        return f"{hundreds}+{remainder:06.3f}"


def str_to_station(station_str: str, imperial: bool = True) -> float:
    """Parse a station string to meters.

    Args:
        station_str: Station string like "10+50.00".
        imperial: If True, input is in feet. Otherwise metric.
    """
    parts = station_str.split("+")
    if len(parts) == 2:
        value = float(parts[0]) * 100 + float(parts[1])
    else:
        value = float(station_str)
    if imperial:
        return ft_to_m(value)
    return value
