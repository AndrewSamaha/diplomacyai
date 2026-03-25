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
        0.2 * float(adjacent_foreign_militaries_to_destination)
        + 0.2 * float(immediate_contestation_count)
        + 0.2 * float(enemy_support_potential)
        + 0.2 * float(destination_degree)
        - 0.2 * float(holdability_next_turn)
    )
