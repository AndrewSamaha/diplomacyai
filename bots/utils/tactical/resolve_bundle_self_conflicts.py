"""Resolve self-conflicting move orders within one power's bundle."""

from collections import defaultdict

from bots.utils.tactical.base_location import base_location
from bots.utils.tactical.move_destination import move_destination
from bots.utils.tactical.order_source_location import order_source_location


def resolve_bundle_self_conflicts(orders: list[str]) -> dict[str, object]:
    """Resolve same-destination own moves as bounces and return metadata."""
    destination_to_indices: dict[str, list[int]] = defaultdict(list)
    for idx, order in enumerate(orders):
        destination = move_destination(order)
        if destination:
            destination_to_indices[base_location(destination)].append(idx)

    bounced_indices: set[int] = set()
    conflict_groups: list[dict[str, object]] = []
    for destination, indices in sorted(destination_to_indices.items()):
        if len(indices) <= 1:
            continue
        bounced_indices.update(indices)
        conflict_groups.append(
            {
                "destination": destination,
                "order_indices": list(indices),
                "orders": [orders[idx] for idx in indices],
            }
        )

    effective_orders: list[str] = []
    per_order: list[dict[str, str]] = []
    for idx, intended_order in enumerate(orders):
        if idx in bounced_indices:
            source = order_source_location(intended_order) or ""
            parts = str(intended_order).upper().split()
            unit_type = parts[0] if parts else "A"
            effective_order = f"{unit_type} {source} H".strip()
            result = "bounced_self_conflict"
        else:
            effective_order = intended_order
            result = "as_intended"

        effective_orders.append(effective_order)
        per_order.append(
            {
                "intended_order": intended_order,
                "effective_order": effective_order,
                "result": result,
            }
        )

    return {
        "effective_orders": effective_orders,
        "per_order": per_order,
        "self_conflict_groups": conflict_groups,
        "n_self_bounced_moves": len(bounced_indices),
    }
