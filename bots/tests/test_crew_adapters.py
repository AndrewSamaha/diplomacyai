"""Unit tests for crew adapter registry."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bots.crews.adapters import (
    CREW_PICK_BEST,
    CREW_RANDOM,
    CREW_TACTICAL,
    DEFAULT_CREW,
    NOCREW_HOLDONLY,
    NOCREW_RANDOM,
    get_crew_adapter,
    is_no_crew_strategy,
)
from bots.tools.get_tactical_order_bundle import GetTacticalOrderBundleTool


class _Game:
    pass


def test_unknown_crew_uses_default_adapter():
    adapter = get_crew_adapter("does_not_exist")
    assert adapter.name == DEFAULT_CREW
    assert adapter.name == CREW_RANDOM


def test_pick_best_adapter_flags_taunt_support():
    adapter = get_crew_adapter(CREW_PICK_BEST)
    assert adapter.supports_taunt is True


def test_tactical_adapter_provides_bundle_tool():
    adapter = get_crew_adapter(CREW_TACTICAL)
    tools = adapter.tools_factory(_Game())
    assert len(tools) == 1
    assert isinstance(tools[0], GetTacticalOrderBundleTool)


def test_no_crew_strategy_sentinel():
    assert is_no_crew_strategy(NOCREW_RANDOM) is True
    assert is_no_crew_strategy(NOCREW_HOLDONLY) is True
    assert is_no_crew_strategy(CREW_RANDOM) is False
