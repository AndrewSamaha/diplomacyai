"""Compute deterministic risk score for a candidate move."""


def risk_score(
    adjacent_foreign_militaries_to_destination: int,
    immediate_contestation_count: int,
    enemy_support_potential: int,
    destination_degree: int,
    holdability_next_turn: int,
) -> float:
    """Return a deterministic tactical risk score."""
    return (
        1.0 * float(adjacent_foreign_militaries_to_destination)
        + 1.5 * float(immediate_contestation_count)
        + 0.75 * float(enemy_support_potential)
        + 0.25 * float(destination_degree)
        - 0.5 * float(holdability_next_turn)
    )
