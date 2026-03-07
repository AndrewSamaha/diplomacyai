"""Unit tests for tactical beam-search bundle selection."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bots.utils.tactical import select_best_order_bundle


def _hex3x3_loc_abut():
    return {
        "AAA": ["AAB", "ABA", "ABB"],
        "AAB": ["AAA", "AAC", "ABA", "ABB", "ABC"],
        "AAC": ["AAB", "ABB", "ABC"],
        "ABA": ["AAA", "AAB", "ABB", "ACA", "ACB"],
        "ABB": ["AAA", "AAB", "AAC", "ABA", "ABC", "ACA", "ACB", "ACC"],
        "ABC": ["AAB", "AAC", "ABB", "ACB", "ACC"],
        "ACA": ["ABA", "ABB", "ACB"],
        "ACB": ["ABA", "ABB", "ABC", "ACA", "ACC"],
        "ACC": ["ABB", "ABC", "ACB"],
    }


def test_select_best_order_bundle_returns_full_order_set():
    result = select_best_order_bundle(
        power_name="FRANCE",
        possible_orders=[
            {"location": "AAB", "orders": ["A AAB - ABB", "A AAB - AAC", "A AAB H"]},
            {"location": "ABA", "orders": ["A ABA - ABB", "A ABA - AAA", "A ABA H"]},
        ],
        units_by_power={
            "FRANCE": ["A AAB", "A ABA"],
            "AUSTRIA": ["A ABC", "A ACB"],
        },
        centers_by_power={
            "FRANCE": ["AAB", "ABA"],
            "AUSTRIA": ["ABC", "ACB"],
        },
        loc_abut=_hex3x3_loc_abut(),
        supply_centers=["AAA", "AAB", "AAC", "ABA", "ABB", "ABC", "ACA", "ACB", "ACC"],
        beam_width=16,
        include_non_moves=True,
    )

    assert len(result["recommended_orders"]) == 2
    assert isinstance(result["bundle_score"], float)
    assert result["evaluated_bundles"] >= 1
    assert "total" in result["score_breakdown"]


def test_select_best_order_bundle_is_deterministic():
    kwargs = dict(
        power_name="FRANCE",
        possible_orders=[
            {"location": "AAB", "orders": ["A AAB - AAA", "A AAB - AAC"]},
            {"location": "ABA", "orders": ["A ABA - ACA", "A ABA - ABB"]},
        ],
        units_by_power={"FRANCE": ["A AAB", "A ABA"], "AUSTRIA": ["A ABC"]},
        centers_by_power={"FRANCE": ["AAB", "ABA"], "AUSTRIA": ["ABC"]},
        loc_abut=_hex3x3_loc_abut(),
        supply_centers=["AAA", "AAB", "AAC", "ABA", "ABB", "ABC", "ACA", "ACB", "ACC"],
        beam_width=8,
        include_non_moves=True,
    )

    first = select_best_order_bundle(**kwargs)
    second = select_best_order_bundle(**kwargs)

    assert first["recommended_orders"] == second["recommended_orders"]
    assert first["bundle_score"] == second["bundle_score"]


def test_select_best_order_bundle_resolves_self_conflict_moves():
    result = select_best_order_bundle(
        power_name="FRANCE",
        possible_orders=[
            {"location": "AAB", "orders": ["A AAB - ABB"]},
            {"location": "ABA", "orders": ["A ABA - ABB"]},
        ],
        units_by_power={"FRANCE": ["A AAB", "A ABA"], "AUSTRIA": ["A ABC"]},
        centers_by_power={"FRANCE": ["AAB", "ABA"], "AUSTRIA": ["ABC"]},
        loc_abut=_hex3x3_loc_abut(),
        supply_centers=["AAA", "AAB", "AAC", "ABA", "ABB", "ABC", "ACA", "ACB", "ACC"],
        beam_width=8,
        include_non_moves=True,
    )

    assert result["recommended_orders"] == ["A AAB - ABB", "A ABA - ABB"]
    assert result["resolved_orders"] == ["A AAB H", "A ABA H"]
    assert result["resolution_metadata"]["n_self_bounced_moves"] == 2
    assert len(result["resolution_metadata"]["self_conflict_groups"]) == 1
    assert result["score_breakdown"]["destination_conflict_penalty"] == 0.0


def test_select_best_order_bundle_prefers_non_conflicting_bundle():
    result = select_best_order_bundle(
        power_name="FRANCE",
        possible_orders=[
            {"location": "AAB", "orders": ["A AAB - ABB", "A AAB - AAC"]},
            {"location": "ABA", "orders": ["A ABA - ABB", "A ABA - ACA"]},
        ],
        units_by_power={"FRANCE": ["A AAB", "A ABA"], "AUSTRIA": ["A ABC"]},
        centers_by_power={"FRANCE": ["AAB", "ABA"], "AUSTRIA": ["ABC"]},
        loc_abut=_hex3x3_loc_abut(),
        supply_centers=["AAA", "AAB", "AAC", "ABA", "ABB", "ABC", "ACA", "ACB", "ACC"],
        beam_width=16,
        include_non_moves=True,
    )

    destinations = [order.split(" - ")[1] for order in result["recommended_orders"] if " - " in order]
    assert len(destinations) == len(set(destinations))
    assert result["resolution_metadata"]["n_self_bounced_moves"] == 0


def test_select_best_order_bundle_mixed_conflict_and_non_conflict_moves():
    result = select_best_order_bundle(
        power_name="FRANCE",
        possible_orders=[
            {"location": "AAB", "orders": ["A AAB - ACC"]},
            {"location": "ABA", "orders": ["A ABA - ACC"]},
            {"location": "AAA", "orders": ["A AAA - AAB"]},
        ],
        units_by_power={"FRANCE": ["A AAB", "A ABA", "A AAA"], "AUSTRIA": ["A ABC"]},
        centers_by_power={"FRANCE": ["AAB", "ABA", "AAA"], "AUSTRIA": ["ABC"]},
        loc_abut=_hex3x3_loc_abut(),
        supply_centers=["AAA", "AAB", "AAC", "ABA", "ABB", "ABC", "ACA", "ACB", "ACC"],
        beam_width=8,
        include_non_moves=True,
    )

    assert result["recommended_orders"] == ["A AAA - AAB", "A AAB - ACC", "A ABA - ACC"]
    assert result["resolved_orders"] == ["A AAA - AAB", "A AAB H", "A ABA H"]
    assert result["resolution_metadata"]["n_self_bounced_moves"] == 2
