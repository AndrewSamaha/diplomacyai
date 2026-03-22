"""CLI probe for understanding why a hand-crafted bundle does or does not survive beam search."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from bots.utils.tactical.annotate_possible_orders import annotate_possible_orders
from bots.utils.tactical.estimate_bundle_score import estimate_bundle_score
from bots.utils.tactical.base_location import base_location
from bots.utils.tactical.move_destination import move_destination
from bots.utils.tactical.order_source_location import order_source_location
from bots.utils.tactical.select_best_order_bundle import select_best_order_bundle
from bots.utils.tactical.supported_move_order import supported_move_order
from spec.bundle_scoring_harness import load_bundle_search_inputs


DEFAULT_GAME_PATH = Path(__file__).resolve().parent / "game_data" / "3x3a.json"
DEFAULT_PHASE = "F1902M"
DEFAULT_POWER = "AUSTRIA"
DEFAULT_TARGET_ORDERS = [
    "A ABC - ABB",
    "A ACB S A ABC - ABB",
    "A AAC S A ABC - ABB",
    "A ACC - ABC"
]


@dataclass(frozen=True)
class SearchContext:
    annotation_by_order: dict[str, dict[str, object]]
    orders_by_location: dict[str, list[str]]
    ordered_locations: list[str]
    pre_score_by_order: dict[str, float]


def build_search_context(search_inputs, *, include_non_moves: bool) -> SearchContext:
    """Rebuild the production search inputs used by select_best_order_bundle()."""
    annotations = annotate_possible_orders(
        power_name=search_inputs.power_name,
        possible_orders=search_inputs.possible_orders,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
    )
    annotation_by_order = {str(entry["order"]): entry for entry in annotations}

    orders_by_location: dict[str, list[str]] = {}
    pre_score_by_order: dict[str, float] = {}
    for entry in search_inputs.possible_orders:
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

    ordered_locations = sorted(
        [location for location in orders_by_location.keys() if orders_by_location[location]]
    )
    return SearchContext(
        annotation_by_order=annotation_by_order,
        orders_by_location=orders_by_location,
        ordered_locations=ordered_locations,
        pre_score_by_order=pre_score_by_order,
    )


def partial_key(partial_orders: list[str], context: SearchContext) -> float:
    """Mirror the production beam-search partial heuristic."""
    value = 0.0
    destination_counts: dict[str, int] = {}
    partial_order_set = {str(order).upper() for order in partial_orders}
    assigned_sources = {
        order_source_location(str(order))
        for order in partial_orders
        if order_source_location(str(order))
    }
    for order in partial_orders:
        value += context.pre_score_by_order.get(order, 0.0)
        destination = move_destination(order)
        if destination:
            dst = base_location(destination)
            destination_counts[dst] = destination_counts.get(dst, 0) + 1
        supported_order = supported_move_order(order)
        if supported_order:
            supported_source = order_source_location(supported_order)
            if supported_source in assigned_sources and supported_order not in partial_order_set:
                value -= 2.0
    duplicate_penalty = sum(max(count - 1, 0) * 2.0 for count in destination_counts.values())
    return value - duplicate_penalty


def format_score(score: float) -> str:
    return f"{score:.3f}"


def investigate_bundle(
    game_path: Path,
    phase_name: str,
    power_name: str,
    target_orders: list[str],
    *,
    beam_width: int,
    include_non_moves: bool,
) -> None:
    """Print a beam-search investigation for a hand-crafted bundle."""
    search_inputs = load_bundle_search_inputs(game_path, phase_name, power_name)
    context = build_search_context(search_inputs, include_non_moves=include_non_moves)
    target_by_source = {
        order_source_location(order): order
        for order in target_orders
    }

    print("Bundle Search Probe")
    print(f"game={game_path}")
    print(f"phase={phase_name} power={power_name} beam_width={beam_width} include_non_moves={include_non_moves}")
    print()

    print("Target bundle")
    for order in target_orders:
        print(f"  {order}")
    print()

    print("Legality")
    for location in context.ordered_locations:
        target_order = target_by_source.get(location)
        legal_orders = context.orders_by_location.get(location, [])
        if target_order is None:
            print(f"  {location}: missing target order")
            continue
        print(
            f"  {location}: {'legal' if target_order in legal_orders else 'ILLEGAL'} "
            f"(pre_score={format_score(context.pre_score_by_order.get(target_order, 0.0))})"
        )
    print()

    target_score, target_breakdown, _ = estimate_bundle_score(
        power_name=search_inputs.power_name,
        orders=target_orders,
        annotation_by_order=context.annotation_by_order,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
        supply_centers=search_inputs.supply_centers,
    )
    print("Target final score")
    print(f"  total={format_score(target_score)} breakdown={target_breakdown}")
    print()

    bundle = select_best_order_bundle(
        power_name=search_inputs.power_name,
        possible_orders=search_inputs.possible_orders,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
        supply_centers=search_inputs.supply_centers,
        beam_width=beam_width,
        include_non_moves=include_non_moves,
    )
    matching_candidates = [
        candidate
        for candidate in bundle["candidate_bundles"]
        if candidate["intended_orders"] == target_orders
    ]
    print("Finalists")
    print(f"  recommended={bundle['recommended_orders']}")
    print(f"  recommended_score={bundle['bundle_score']}")
    print(f"  target_in_finalists={bool(matching_candidates)}")
    if matching_candidates:
        print(f"  target_rank={matching_candidates[0]['bundle_rank']}")
    print()

    print("Beam progression")
    beam: list[list[str]] = [[]]
    for depth, location in enumerate(context.ordered_locations, start=1):
        options = sorted(
            context.orders_by_location[location],
            key=lambda order: (-context.pre_score_by_order.get(order, 0.0), order),
        )
        expanded: list[list[str]] = []
        for partial in beam:
            for order in options:
                expanded.append(partial + [order])
        expanded.sort(key=lambda partial: (-partial_key(partial, context), tuple(partial)))
        beam = expanded[:beam_width]

        target_prefix: list[str] = []
        prefix_complete = True
        for prefix_location in context.ordered_locations[:depth]:
            target_order = target_by_source.get(prefix_location)
            if target_order is None:
                prefix_complete = False
                break
            target_prefix.append(target_order)

        if not prefix_complete:
            print(f"  depth={depth} location={location} target prefix incomplete")
            continue

        target_score_partial = partial_key(target_prefix, context)
        rank = None
        for index, partial in enumerate(expanded, start=1):
            if partial == target_prefix:
                rank = index
                break
        kept = rank is not None and rank <= beam_width
        print(
            f"  depth={depth} location={location} target_partial={target_prefix} "
            f"partial_score={format_score(target_score_partial)} rank={rank} kept={kept}"
        )

        if rank is None or rank > beam_width:
            print("    nearby contenders:")
            for index, partial in enumerate(expanded[: min(beam_width + 3, len(expanded))], start=1):
                marker = " <- cutoff" if index == beam_width else ""
                print(
                    f"      {index:>3}: score={format_score(partial_key(partial, context))} "
                    f"{partial}{marker}"
                )
            print()
            break


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe why a hand-crafted bundle drops out of beam search.")
    parser.add_argument("--game-path", type=Path, default=DEFAULT_GAME_PATH)
    parser.add_argument("--phase", default=DEFAULT_PHASE)
    parser.add_argument("--power", default=DEFAULT_POWER)
    parser.add_argument("--beam-width", type=int, default=64)
    parser.add_argument("--exclude-non-moves", action="store_true")
    parser.add_argument(
        "--order",
        dest="orders",
        action="append",
        help="Add one target order. May be provided multiple times.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_orders = args.orders or list(DEFAULT_TARGET_ORDERS)
    investigate_bundle(
        args.game_path,
        args.phase,
        args.power,
        target_orders,
        beam_width=args.beam_width,
        include_non_moves=not args.exclude_non_moves,
    )


if __name__ == "__main__":
    main()
