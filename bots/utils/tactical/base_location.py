"""Normalize map locations to their base province code."""


def base_location(location: str | None) -> str:
    """Return a 3-letter upper-case base location code."""
    if not location:
        return ""
    return str(location).upper()[:3]
