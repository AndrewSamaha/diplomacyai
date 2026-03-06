"""Unit tests for tactical move annotation tool."""

from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bots.tools.get_tactical_move_annotations import GetTacticalMoveAnnotationsTool


class _Power:
    def __init__(self, name, units, centers):
        self.name = name
        self.units = units
        self.centers = centers


class _Map:
    def __init__(self, loc_abut):
        self.loc_abut = loc_abut


class _Game:
    def __init__(self):
        self._phase = "S1901M"
        self.map = _Map(
            {
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
        )
        self.powers = {
            "FRANCE": _Power("FRANCE", ["A AAB", "A ABA"], ["AAB", "ABA"]),
            "AUSTRIA": _Power("AUSTRIA", ["A ABC", "A ACB"], ["ABC", "ACB"]),
        }

    def get_current_phase(self):
        return self._phase

    def get_orderable_locations(self, power_name):
        if power_name.upper() == "FRANCE":
            return ["AAB", "ABA"]
        return []

    def get_all_possible_orders(self):
        return {
            "AAB": ["A AAB - ABB", "A AAB - AAC", "A AAB H"],
            "ABA": ["A ABA - ABB", "A ABA - AAA", "A ABA H"],
        }


def test_tool_returns_moves_with_selected_annotations_only():
    tool = GetTacticalMoveAnnotationsTool(game=_Game())

    raw = tool._run(
        power_name="FRANCE",
        annotations=["supply_center_delta_if_success", "net_score"],
        include_non_moves=False,
    )
    data = json.loads(raw)

    assert data["power_name"] == "FRANCE"
    assert data["selected_annotations"] == ["supply_center_delta_if_success", "net_score"]
    assert len(data["possible_moves"]) == 4
    for move in data["possible_moves"]:
        assert move["is_move"] is True
        assert set(move["metrics"].keys()) == {"supply_center_delta_if_success", "net_score"}


def test_tool_can_include_non_moves():
    tool = GetTacticalMoveAnnotationsTool(game=_Game())

    raw = tool._run(power_name="FRANCE", include_non_moves=True)
    data = json.loads(raw)

    assert len(data["possible_moves"]) == 6
    non_moves = [item for item in data["possible_moves"] if not item["is_move"]]
    assert len(non_moves) == 2
    for item in non_moves:
        assert item["metrics"] is None
        assert item["move_rank"] is None


def test_tool_returns_error_for_unknown_annotations_or_power():
    tool = GetTacticalMoveAnnotationsTool(game=_Game())

    bad_annotations = json.loads(tool._run(power_name="FRANCE", annotations=["not_a_metric"]))
    assert "error" in bad_annotations
    assert "Unknown annotations requested" in bad_annotations["error"]

    bad_power = json.loads(tool._run(power_name="GERMANY"))
    assert "error" in bad_power
    assert "Unknown power requested" in bad_power["error"]
