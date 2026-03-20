"""Helpers for extracting the supported move from an offensive support order."""

from bots.utils.tactical.base_location import base_location


def supported_move_order(order: str) -> str | None:
    """Return canonical supported move order text from a support-to-move order, else None."""
    parts = str(order).upper().split()
    if len(parts) < 7:
        return None
    if parts[0] not in {"A", "F"} or parts[2] != "S":
        return None
    if parts[3] not in {"A", "F"} or parts[5] != "-":
        return None
    return f"{parts[3]} {base_location(parts[4])} - {base_location(parts[6])}"


def supported_move_destination(order: str) -> str | None:
    """Return destination for a support-to-move order, else None."""
    supported = supported_move_order(order)
    if not supported:
        return None
    return supported.split()[-1]
