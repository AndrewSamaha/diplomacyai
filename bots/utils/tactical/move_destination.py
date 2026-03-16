"""Extract destination from a move order."""


def move_destination(order: str) -> str | None:
    """Return destination location from a move order, else None."""
    parts = str(order).upper().split()
    if len(parts) < 4:
        return None
    if parts[0] not in {"A", "F"}:
        return None
    if parts[2] != "-":
        return None
    return parts[3]
