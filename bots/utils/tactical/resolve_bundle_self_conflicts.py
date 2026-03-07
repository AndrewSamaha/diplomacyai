"""Resolve deterministic own-bundle interactions before tactical scoring."""

from collections import defaultdict
from typing import Callable

from bots.utils.tactical.base_location import base_location
from bots.utils.tactical.move_destination import move_destination
from bots.utils.tactical.order_source_location import order_source_location

ResolverState = dict[str, object]
ResolverRule = Callable[[ResolverState], bool]

RULE_DUPLICATE_MOVE_DESTINATION = "duplicate_move_destination"
RULE_MOVE_INTO_FRIENDLY_OCCUPIED = "move_into_friendly_occupied"


def _is_move(order: str) -> bool:
    return move_destination(order) is not None


def _to_hold_order(order: str) -> str:
    source = order_source_location(order) or ""
    parts = str(order).upper().split()
    unit_type = parts[0] if parts else "A"
    return f"{unit_type} {source} H".strip()


def _mark_bounce(state: ResolverState, idx: int, *, reason: str) -> bool:
    effective_orders = state["effective_orders"]
    intended_orders = state["intended_orders"]
    if idx < 0 or idx >= len(effective_orders):
        return False
    current = str(effective_orders[idx])
    if not _is_move(current):
        return False

    hold_order = _to_hold_order(str(intended_orders[idx]))
    effective_orders[idx] = hold_order

    reasons = state["order_reason_by_index"]
    reason_list = reasons.get(idx)
    if reason_list is None:
        reason_list = []
        reasons[idx] = reason_list
    reason_list.append(reason)
    return True


def _rule_duplicate_move_destinations(state: ResolverState) -> bool:
    effective_orders = state["effective_orders"]

    destination_to_indices: dict[str, list[int]] = defaultdict(list)
    for idx, order in enumerate(effective_orders):
        destination = move_destination(str(order))
        if destination:
            destination_to_indices[base_location(destination)].append(idx)

    changed = False
    groups: list[dict[str, object]] = []
    for destination, indices in sorted(destination_to_indices.items()):
        if len(indices) <= 1:
            continue
        groups.append(
            {
                "destination": destination,
                "order_indices": list(indices),
                "orders": [str(effective_orders[idx]) for idx in indices],
            }
        )
        for idx in indices:
            if _mark_bounce(state, idx, reason=RULE_DUPLICATE_MOVE_DESTINATION):
                changed = True

    if groups:
        state["self_conflict_groups"] = groups
    return changed


def _rule_move_into_friendly_occupied(state: ResolverState) -> bool:
    effective_orders = state["effective_orders"]

    unit_by_source: dict[str, int] = {}
    for idx, order in enumerate(effective_orders):
        source = order_source_location(str(order))
        if source:
            unit_by_source[source] = idx

    staying_sources: set[str] = set()
    for source, idx in unit_by_source.items():
        if not _is_move(str(effective_orders[idx])):
            staying_sources.add(source)

    to_bounce: list[int] = []
    groups: list[dict[str, object]] = []
    for idx, order in enumerate(effective_orders):
        destination = move_destination(str(order))
        if not destination:
            continue
        destination_base = base_location(destination)
        if destination_base not in staying_sources:
            continue
        occupant_idx = unit_by_source.get(destination_base)
        if occupant_idx is None:
            continue
        to_bounce.append(idx)
        groups.append(
            {
                "destination": destination_base,
                "moving_order_index": idx,
                "moving_order": str(order),
                "occupying_order_index": occupant_idx,
                "occupying_effective_order": str(effective_orders[occupant_idx]),
            }
        )

    changed = False
    for idx in to_bounce:
        if _mark_bounce(state, idx, reason=RULE_MOVE_INTO_FRIENDLY_OCCUPIED):
            changed = True

    if groups:
        state["friendly_occupied_conflicts"] = groups
    return changed


RESOLUTION_RULES: list[ResolverRule] = [
    _rule_duplicate_move_destinations,
    _rule_move_into_friendly_occupied,
]


def resolve_bundle_self_conflicts(orders: list[str]) -> dict[str, object]:
    """Resolve deterministic own-bundle interactions and return metadata."""
    state: ResolverState = {
        "intended_orders": [str(order) for order in orders],
        "effective_orders": [str(order) for order in orders],
        "order_reason_by_index": {},
        "self_conflict_groups": [],
        "friendly_occupied_conflicts": [],
    }

    max_iterations = max(1, len(orders) + 2)
    iterations = 0
    while iterations < max_iterations:
        iterations += 1
        changed = False
        for rule in RESOLUTION_RULES:
            if rule(state):
                changed = True
        if not changed:
            break

    intended_orders = state["intended_orders"]
    effective_orders = state["effective_orders"]
    reason_by_index = state["order_reason_by_index"]

    per_order: list[dict[str, str]] = []
    n_self_bounced_moves = 0
    for idx, intended_order in enumerate(intended_orders):
        effective_order = str(effective_orders[idx])
        reasons = reason_by_index.get(idx, [])
        if reasons:
            result = f"bounced_{reasons[-1]}"
            n_self_bounced_moves += 1
        else:
            result = "as_intended"

        per_order.append(
            {
                "intended_order": str(intended_order),
                "effective_order": effective_order,
                "result": result,
            }
        )

    return {
        "effective_orders": [str(order) for order in effective_orders],
        "per_order": per_order,
        "self_conflict_groups": state["self_conflict_groups"],
        "friendly_occupied_conflicts": state["friendly_occupied_conflicts"],
        "n_self_bounced_moves": n_self_bounced_moves,
        "resolver_iterations": iterations,
    }
