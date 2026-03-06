"""Deterministic tactical annotations for possible orders."""

from bots.utils.tactical.base_location import base_location
from bots.utils.tactical.build_center_owner import build_center_owner
from bots.utils.tactical.build_units_by_power import build_units_by_power
from bots.utils.tactical.centerity_scores import centerity_scores
from bots.utils.tactical.move_destination import move_destination
from bots.utils.tactical.neighbors_for import neighbors_for
from bots.utils.tactical.risk_score import risk_score
from bots.utils.tactical.value_score import value_score


def annotate_possible_orders(
    power_name: str,
    possible_orders: list[dict[str, object]],
    units_by_power: dict[str, list[str]],
    centers_by_power: dict[str, list[str]],
    loc_abut: dict[str, list[str]],
) -> list[dict[str, object]]:
    """Annotate possible orders with deterministic tactical features.

    Returns a list of annotations. Move orders include metrics and deterministic
    ranking (`move_rank`) using net/value/risk/order tie-breaks.
    """
    me = str(power_name).upper()
    unit_locs = build_units_by_power(units_by_power)
    center_owner = build_center_owner(centers_by_power)
    centrality = centerity_scores(loc_abut)

    my_units = unit_locs.get(me, set())
    enemy_units_by_power = {
        power: locs for power, locs in unit_locs.items() if power != me
    }

    annotations: list[dict[str, object]] = []

    for entry in possible_orders:
        source = base_location(str(entry.get("location", "")))
        orders = entry.get("orders", [])
        if not isinstance(orders, list):
            orders = []

        for order in orders:
            order_text = str(order)
            destination = move_destination(order_text)
            is_move = destination is not None

            base_annotation: dict[str, object] = {
                "order": order_text,
                "location": source,
                "is_move": is_move,
                "destination": destination,
                "metrics": None,
                "move_rank": None,
            }

            if not is_move:
                annotations.append(base_annotation)
                continue

            dst = base_location(destination)
            src = source
            dst_neighbors = neighbors_for(dst, loc_abut)
            src_neighbors = neighbors_for(src, loc_abut)

            foreign_adjacent_units = 0
            contesting_powers: set[str] = set()
            enemy_support_potential = 0
            for enemy_power, enemy_locs in enemy_units_by_power.items():
                adjacent_to_dst = enemy_locs & dst_neighbors
                adjacent_to_src = enemy_locs & src_neighbors
                if adjacent_to_dst:
                    foreign_adjacent_units += len(adjacent_to_dst)
                    contesting_powers.add(enemy_power)
                enemy_support_potential += len(adjacent_to_dst | adjacent_to_src)

            own_units_excluding_src = {loc for loc in my_units if loc != src}
            own_support_potential = len((own_units_excluding_src & dst_neighbors) | (own_units_excluding_src & src_neighbors))

            destination_degree = len(dst_neighbors)
            supply_center_delta_if_success = int(center_owner.get(dst) != me)
            holdability_next_turn = (1 + len(own_units_excluding_src & dst_neighbors)) - foreign_adjacent_units
            is_reversible = any(neighbor not in {loc for locs in enemy_units_by_power.values() for loc in locs}
                                for neighbor in dst_neighbors)
            centerity_gain = float(centrality.get(dst, 0.0) - centrality.get(src, 0.0))

            value = value_score(
                supply_center_delta_if_success=supply_center_delta_if_success,
                centerity_gain=centerity_gain,
                holdability_next_turn=holdability_next_turn,
                own_support_potential=own_support_potential,
            )
            risk = risk_score(
                adjacent_foreign_militaries_to_destination=foreign_adjacent_units,
                immediate_contestation_count=len(contesting_powers),
                enemy_support_potential=enemy_support_potential,
                destination_degree=destination_degree,
                holdability_next_turn=holdability_next_turn,
            )
            net = value - risk

            base_annotation["metrics"] = {
                "supply_center_delta_if_success": supply_center_delta_if_success,
                "adjacent_foreign_militaries_to_destination": foreign_adjacent_units,
                "immediate_contestation_count": len(contesting_powers),
                "own_support_potential": own_support_potential,
                "enemy_support_potential": enemy_support_potential,
                "destination_degree": destination_degree,
                "holdability_next_turn": holdability_next_turn,
                "is_reversible": is_reversible,
                "centerity_gain": round(centerity_gain, 6),
                "value_score": round(value, 6),
                "risk_score": round(risk, 6),
                "net_score": round(net, 6),
            }
            annotations.append(base_annotation)

    move_annotations = [a for a in annotations if a["is_move"]]
    move_annotations.sort(
        key=lambda annotation: (
            -float(annotation["metrics"]["net_score"]),
            -float(annotation["metrics"]["value_score"]),
            float(annotation["metrics"]["risk_score"]),
            str(annotation["order"]),
        )
    )
    for index, annotation in enumerate(move_annotations, start=1):
        annotation["move_rank"] = index

    return annotations
