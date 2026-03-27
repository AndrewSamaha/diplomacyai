"""Unit tests for non-crew order selection helpers."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bots.utils import random_orders


class _Game:
    def __init__(self, orderable_locations, possible_orders):
        self._orderable_locations = orderable_locations
        self._possible_orders = possible_orders

    def get_orderable_locations(self, power_name):
        assert power_name == "FRANCE"
        return self._orderable_locations

    def get_all_possible_orders(self):
        return self._possible_orders


def test_get_hold_only_orders_prefers_hold_without_random_fallback(monkeypatch):
    game = _Game(
        ["PAR", "BRE"],
        {
            "PAR": ["A PAR H", "A PAR - BUR"],
            "BRE": ["F BRE H", "F BRE - MAO"],
        },
    )

    def _unexpected_choice(_):
        raise AssertionError("random.choice should not be called when HOLD is available")

    monkeypatch.setattr(random_orders.random, "choice", _unexpected_choice)

    assert random_orders.get_hold_only_orders(game, "FRANCE") == ["A PAR H", "F BRE H"]


def test_get_hold_only_orders_falls_back_to_random_when_hold_missing(monkeypatch):
    game = _Game(
        ["PAR", "MAR"],
        {
            "PAR": ["A PAR H", "A PAR - BUR"],
            "MAR": ["A MAR - SPA", "A MAR S A PAR - BUR"],
        },
    )

    calls = []

    def _deterministic_choice(options):
        calls.append(list(options))
        return options[-1]

    monkeypatch.setattr(random_orders.random, "choice", _deterministic_choice)

    assert random_orders.get_hold_only_orders(game, "FRANCE") == [
        "A PAR H",
        "A MAR S A PAR - BUR",
    ]
    assert calls == [["A MAR - SPA", "A MAR S A PAR - BUR"]]
