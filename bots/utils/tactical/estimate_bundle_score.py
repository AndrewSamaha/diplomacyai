"""Estimate deterministic tactical score for a complete order bundle."""

from bots.utils.tactical.base_location import base_location
from bots.utils.tactical.move_destination import move_destination
from bots.utils.tactical.neighbors_for import neighbors_for
from bots.utils.tactical.order_source_location import order_source_location
from bots.utils.tactical.resolve_bundle_self_conflicts import resolve_bundle_self_conflicts
from bots.utils.tactical.supported_move_order import supported_move_order


def estimate_bundle_score(
    power_name: str,
    orders: list[str],
    annotation_by_order: dict[str, dict[str, object]],
    units_by_power: dict[str, list[str]],
    centers_by_power: dict[str, list[str]],
    loc_abut: dict[str, list[str]],
    supply_centers: list[str] | None = None,
) -> tuple[float, dict[str, float], dict[str, object]]:
    """Return (score, breakdown, resolution) for a full list of selected orders."""
    me = power_name.upper()

    enemy_units: set[str] = set()
    occupied_by_enemy: set[str] = set()
    for power, units in units_by_power.items():
        if power.upper() == me:
            continue
        for unit in units:
            parts = str(unit).lstrip("*").split()
            if len(parts) >= 2:
                location = base_location(parts[1])
                enemy_units.add(location)
                occupied_by_enemy.add(location)

    my_centers = {base_location(center) for center in centers_by_power.get(me, [])}
    supply_set = {base_location(center) for center in (supply_centers or [])}

    center_owner: dict[str, str] = {}
    for owner, centers in centers_by_power.items():
        for center in centers:
            center_owner[base_location(center)] = owner.upper()

    resolution = resolve_bundle_self_conflicts(orders)
    effective_orders = [str(order) for order in resolution["effective_orders"]]
    effective_order_set = {str(order).upper() for order in effective_orders}

    base_total = 0.0
    move_destinations: list[str] = []
    move_sources: list[str] = []
    support_count_by_supported_order: dict[str, int] = {}

    for order in effective_orders:
        annotation = annotation_by_order.get(order, {})
        metrics = annotation.get("metrics")
        if isinstance(metrics, dict) and "net_score" in metrics:
            supported_order = supported_move_order(order)
            if not supported_order or supported_order in effective_order_set:
                base_total += float(metrics["net_score"])
        elif " H" in order.upper():
            base_total += 0.1

        destination = move_destination(order)
        source = order_source_location(order)
        if destination:
            move_destinations.append(base_location(destination))
        if destination and source:
            move_sources.append(base_location(source))

        supported_order = supported_move_order(order)
        if supported_order:
            support_count_by_supported_order[supported_order] = support_count_by_supported_order.get(supported_order, 0) + 1

    destination_counts: dict[str, int] = {}
    for dst in move_destinations:
        destination_counts[dst] = destination_counts.get(dst, 0) + 1
    destination_conflict_penalty = 0.0

    capture_bonus = 0.0
    for dst in set(move_destinations):
        if dst in supply_set and center_owner.get(dst) != me:
            capture_bonus += 1.0

    moved_dest_set = set(move_destinations)
    leave_center_penalty = 0.0
    for source in move_sources:
        if source in my_centers and source not in moved_dest_set:
            leave_center_penalty += 0.5

    exposure_penalty = 0.0
    for dst in move_destinations:
        exposure_penalty += 0.25 * float(len(neighbors_for(dst, loc_abut) & enemy_units))

    cohesion_bonus = 0.0
    for i, left in enumerate(move_destinations):
        for right in move_destinations[i + 1:]:
            if right in neighbors_for(left, loc_abut):
                cohesion_bonus += 0.15

    supported_enemy_attack_bonus = 0.0
    supported_enemy_center_attack_bonus = 0.0
    unsupported_enemy_attack_penalty = 0.0
    outgunned_supported_attack_penalty = 0.0
    supports_enemy_move_penalty = 0.0
    supports_friendly_move_bonus = 0.0
    dangling_support_penalty = 0.0
    for order in effective_orders:
        metrics = annotation_by_order.get(order, {}).get("metrics")
        if not isinstance(metrics, dict):
            continue
        if int(metrics.get("supports_enemy_move", 0) or 0):
            supports_enemy_move_penalty += 2.5
        elif int(metrics.get("supports_friendly_move", 0) or 0):
            supported_order = supported_move_order(order)
            if supported_order and supported_order in effective_order_set:
                supports_friendly_move_bonus += 0.2
            else:
                dangling_support_penalty += 2.0

    for order in effective_orders:
        destination = move_destination(order)
        if not destination:
            continue
        move_key = str(order).upper()
        dst = base_location(destination)
        if dst not in occupied_by_enemy:
            continue

        support_count = support_count_by_supported_order.get(move_key, 0)
        metrics = annotation_by_order.get(order, {}).get("metrics")
        enemy_support_potential = 0
        if isinstance(metrics, dict):
            enemy_support_potential = int(metrics.get("enemy_support_potential", 0) or 0)

        if support_count > 0:
            supported_enemy_attack_bonus += 0.9 + (0.15 * float(max(support_count - 1, 0)))
            if dst in supply_set and center_owner.get(dst) != me:
                supported_enemy_center_attack_bonus += 0.5
            projected_attack_strength = 1 + support_count
            projected_enemy_strength = 1 + enemy_support_potential
            if projected_attack_strength <= projected_enemy_strength:
                outgunned_supported_attack_penalty += 0.35 * float(projected_enemy_strength - projected_attack_strength + 1)
        else:
            unsupported_enemy_attack_penalty += 0.7

    total = (
        base_total
        + capture_bonus
        + cohesion_bonus
        + supported_enemy_attack_bonus
        + supported_enemy_center_attack_bonus
        + supports_friendly_move_bonus
        - destination_conflict_penalty
        - leave_center_penalty
        - exposure_penalty
        - unsupported_enemy_attack_penalty
        - outgunned_supported_attack_penalty
        - supports_enemy_move_penalty
        - dangling_support_penalty
    )

    breakdown = {
        "base_total": round(base_total, 6),
        "capture_bonus": round(capture_bonus, 6),
        "cohesion_bonus": round(cohesion_bonus, 6),
        "supported_enemy_attack_bonus": round(supported_enemy_attack_bonus, 6),
        "supported_enemy_center_attack_bonus": round(supported_enemy_center_attack_bonus, 6),
        "supports_friendly_move_bonus": round(supports_friendly_move_bonus, 6),
        "destination_conflict_penalty": round(destination_conflict_penalty, 6),
        "leave_center_penalty": round(leave_center_penalty, 6),
        "exposure_penalty": round(exposure_penalty, 6),
        "unsupported_enemy_attack_penalty": round(unsupported_enemy_attack_penalty, 6),
        "outgunned_supported_attack_penalty": round(outgunned_supported_attack_penalty, 6),
        "supports_enemy_move_penalty": round(supports_enemy_move_penalty, 6),
        "dangling_support_penalty": round(dangling_support_penalty, 6),
        "total": round(total, 6),
    }
    return total, breakdown, resolution
