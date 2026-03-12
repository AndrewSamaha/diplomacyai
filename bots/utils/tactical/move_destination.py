"""Extract destination from a move order."""


def move_destination(order: str) -> str | None:
    """Return destination location from a move order, else None."""
    if " - " not in order:
        return None
    return order.rsplit(" - ", 1)[1].split()[0].upper()
