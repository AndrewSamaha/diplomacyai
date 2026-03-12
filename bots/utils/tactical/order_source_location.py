"""Extract source location from an order string."""

from bots.utils.tactical.base_location import base_location


def order_source_location(order: str) -> str | None:
    """Return source base location for an order, if any."""
    parts = str(order).upper().split()
    if len(parts) >= 2 and parts[0] in {"A", "F"}:
        return base_location(parts[1])
    return None
