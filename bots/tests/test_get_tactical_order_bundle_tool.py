"""Unit tests for tactical order-bundle tool."""

from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bots.tools.get_tactical_order_bundle import GetTacticalOrderBundleTool


class _Power:
    def __init__(self, name, units, centers):
        self.name = name
        self.units = units
        self.centers = centers


class _Map:
    def __init__(self, loc_abut, scs):
        self.loc_abut = loc_abut
        self.scs = scs


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
            },
            ["AAA", "AAB", "AAC", "ABA", "ABB", "ABC", "ACA", "ACB", "ACC"],
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


def test_tool_returns_full_orders_and_bundle_metadata():
    tool = GetTacticalOrderBundleTool(game=_Game())

    payload = json.loads(tool._run(power_name="FRANCE", beam_width=16))
    assert payload["power_name"] == "FRANCE"
    assert len(payload["recommended_orders"]) == 2
    assert len(payload["resolved_orders"]) == 2
    assert isinstance(payload["bundle_score"], float)
    assert payload["beam_width"] == 16
    assert "total" in payload["score_breakdown"]
    assert "n_self_bounced_moves" in payload["resolution_metadata"]


def test_tool_returns_error_for_bad_annotation_or_power():
    tool = GetTacticalOrderBundleTool(game=_Game())

    bad_ann = json.loads(tool._run(power_name="FRANCE", annotations=["bad_metric"]))
    assert "error" in bad_ann

    bad_power = json.loads(tool._run(power_name="GERMANY"))
    assert "error" in bad_power
