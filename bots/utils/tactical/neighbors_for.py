"""Read normalized neighbors for a location from map adjacency."""

from bots.utils.tactical.base_location import base_location


def neighbors_for(location: str, loc_abut: dict[str, list[str]]) -> set[str]:
    """Return neighbor base locations for a location."""
    if not location:
        return set()
    key = location.upper()
    values = loc_abut.get(key)
    if values is None:
        values = loc_abut.get(location.lower())
    if values is None:
        values = []
    return {base_location(value) for value in values if base_location(value)}
