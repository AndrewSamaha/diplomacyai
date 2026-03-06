"""Unit tests for deterministic tactical annotations."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bots.utils.tactical import annotate_possible_orders


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


def test_annotate_possible_orders_output_shape_and_keys():
    annotations = annotate_possible_orders(
        power_name="FRANCE",
        possible_orders=[
            {
                "location": "AAB",
                "orders": ["A AAB - ABB", "A AAB - AAC", "A AAB H"],
            },
            {
                "location": "ABA",
                "orders": ["A ABA - ABB", "A ABA - AAA", "A ABA H"],
            },
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
    )

    assert len(annotations) == 6
    for annotation in annotations:
        assert set(annotation.keys()) == {
            "order",
            "location",
            "is_move",
            "destination",
            "metrics",
            "move_rank",
        }
        if annotation["is_move"]:
            assert annotation["metrics"] is not None
            assert set(annotation["metrics"].keys()) == {
                "supply_center_delta_if_success",
                "adjacent_foreign_militaries_to_destination",
                "immediate_contestation_count",
                "own_support_potential",
                "enemy_support_potential",
                "destination_degree",
                "holdability_next_turn",
                "is_reversible",
                "centerity_gain",
                "value_score",
                "risk_score",
                "net_score",
            }
            assert isinstance(annotation["move_rank"], int)
        else:
            assert annotation["metrics"] is None
            assert annotation["move_rank"] is None


def test_center_move_has_higher_contestation_than_edge_move():
    annotations = annotate_possible_orders(
        power_name="FRANCE",
        possible_orders=[
            {"location": "ABA", "orders": ["A ABA - ABB", "A ABA - AAA"]},
        ],
        units_by_power={
            "FRANCE": ["A ABA", "A AAB"],
            "AUSTRIA": ["A ABC", "A ACB"],
        },
        centers_by_power={
            "FRANCE": ["AAB", "ABA"],
            "AUSTRIA": ["ABC", "ACB"],
        },
        loc_abut=_hex3x3_loc_abut(),
    )

    by_order = {a["order"]: a for a in annotations}
    center = by_order["A ABA - ABB"]
    edge = by_order["A ABA - AAA"]

    assert center["metrics"]["adjacent_foreign_militaries_to_destination"] > edge["metrics"]["adjacent_foreign_militaries_to_destination"]
    assert center["metrics"]["immediate_contestation_count"] >= edge["metrics"]["immediate_contestation_count"]


def test_move_ranking_is_deterministic_with_tie_break_on_order_text():
    annotations = annotate_possible_orders(
        power_name="FRANCE",
        possible_orders=[
            {"location": "AAB", "orders": ["A AAB - AAA", "A AAB - AAC"]},
        ],
        units_by_power={
            "FRANCE": ["A AAB"],
            "AUSTRIA": ["A ABC"],
        },
        centers_by_power={
            "FRANCE": ["AAB"],
            "AUSTRIA": ["ABC"],
        },
        loc_abut=_hex3x3_loc_abut(),
    )

    moves = [annotation for annotation in annotations if annotation["is_move"]]
    # Ensure ranking exists and is stable between repeated calls.
    ranks_first = {annotation["order"]: annotation["move_rank"] for annotation in moves}

    annotations_second = annotate_possible_orders(
        power_name="FRANCE",
        possible_orders=[
            {"location": "AAB", "orders": ["A AAB - AAA", "A AAB - AAC"]},
        ],
        units_by_power={
            "FRANCE": ["A AAB"],
            "AUSTRIA": ["A ABC"],
        },
        centers_by_power={
            "FRANCE": ["AAB"],
            "AUSTRIA": ["ABC"],
        },
        loc_abut=_hex3x3_loc_abut(),
    )
    moves_second = [annotation for annotation in annotations_second if annotation["is_move"]]
    ranks_second = {annotation["order"]: annotation["move_rank"] for annotation in moves_second}

    assert ranks_first == ranks_second
