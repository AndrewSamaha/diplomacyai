"""Compute deterministic value score for a candidate move."""


def value_score(
    supply_center_delta_if_success: int,
    centerity_gain: float,
    holdability_next_turn: int,
    own_support_potential: int,
) -> float:
    """Return a deterministic tactical value score."""
    return (
        3.0 * float(supply_center_delta_if_success)
        + 2.0 * float(centerity_gain)
        + 0.5 * float(max(holdability_next_turn, 0))
        + 0.25 * float(own_support_potential)
    )
