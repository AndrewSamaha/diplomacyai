"""Select best full order bundle using deterministic beam search."""

from bots.utils.tactical.annotate_possible_orders import annotate_possible_orders
from bots.utils.tactical.base_location import base_location
from bots.utils.tactical.estimate_bundle_score import estimate_bundle_score
from bots.utils.tactical.move_destination import move_destination


def select_best_order_bundle(
    power_name: str,
    possible_orders: list[dict[str, object]],
    units_by_power: dict[str, list[str]],
    centers_by_power: dict[str, list[str]],
    loc_abut: dict[str, list[str]],
    supply_centers: list[str] | None = None,
    beam_width: int = 32,
    include_non_moves: bool = True,
) -> dict[str, object]:
    """Return a deterministic best bundle of one order per location."""
    beam_width = max(1, int(beam_width))

    annotations = annotate_possible_orders(
        power_name=power_name,
        possible_orders=possible_orders,
        units_by_power=units_by_power,
        centers_by_power=centers_by_power,
        loc_abut=loc_abut,
    )
    annotation_by_order = {str(entry["order"]): entry for entry in annotations}

    orders_by_location: dict[str, list[str]] = {}
    pre_score_by_order: dict[str, float] = {}
    for entry in possible_orders:
        location = base_location(str(entry.get("location", "")))
        raw_orders = entry.get("orders", [])
        if not isinstance(raw_orders, list):
            raw_orders = []
        location_orders = [str(order) for order in raw_orders]

        filtered_orders: list[str] = []
        for order in location_orders:
            annotation = annotation_by_order.get(order, {})
            if not include_non_moves and not annotation.get("is_move", False):
                continue
            filtered_orders.append(order)

        # If filtered list is empty, fallback to raw legal orders for this location.
        if not filtered_orders:
            filtered_orders = location_orders

        orders_by_location[location] = filtered_orders
        for order in filtered_orders:
            metrics = annotation_by_order.get(order, {}).get("metrics")
            if isinstance(metrics, dict) and "net_score" in metrics:
                pre_score_by_order[order] = float(metrics["net_score"])
            elif " H" in order.upper():
                pre_score_by_order[order] = 0.1
            else:
                pre_score_by_order[order] = 0.0

    ordered_locations = sorted([location for location in orders_by_location.keys() if orders_by_location[location]])

    beam: list[list[str]] = [[]]
    for location in ordered_locations:
        options = sorted(
            orders_by_location[location],
            key=lambda order: (-pre_score_by_order.get(order, 0.0), order),
        )
        expanded: list[list[str]] = []
        for partial in beam:
            for order in options:
                expanded.append(partial + [order])

        # Partial pruning: score by sum(pre-score) minus duplicate-destination penalties.
        def partial_key(partial_orders: list[str]):
            value = 0.0
            destination_counts: dict[str, int] = {}
            for order in partial_orders:
                value += pre_score_by_order.get(order, 0.0)
                destination = move_destination(order)
                if destination:
                    dst = base_location(destination)
                    destination_counts[dst] = destination_counts.get(dst, 0) + 1
            penalty = sum(max(count - 1, 0) * 2.0 for count in destination_counts.values())
            return value - penalty

        expanded.sort(key=lambda partial: (-partial_key(partial), tuple(partial)))
        beam = expanded[:beam_width]

    if not beam:
        return {
            "recommended_orders": [],
            "bundle_score": 0.0,
            "score_breakdown": {"total": 0.0},
            "evaluated_bundles": 0,
            "beam_width": beam_width,
        }

    finalists: list[tuple[float, dict[str, float], list[str]]] = []
    for orders in beam:
        score, breakdown = estimate_bundle_score(
            power_name=power_name,
            orders=orders,
            annotation_by_order=annotation_by_order,
            units_by_power=units_by_power,
            centers_by_power=centers_by_power,
            loc_abut=loc_abut,
            supply_centers=supply_centers,
        )
        finalists.append((score, breakdown, orders))

    finalists.sort(key=lambda item: (-item[0], tuple(item[2])))
    best_score, best_breakdown, best_orders = finalists[0]

    return {
        "recommended_orders": best_orders,
        "bundle_score": round(best_score, 6),
        "score_breakdown": best_breakdown,
        "evaluated_bundles": len(finalists),
        "beam_width": beam_width,
    }
