"""Crew adapter registry for comparisonbot crew dispatch."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from bots.crews.ezra_crew import build_ezra_crew
from bots.crews.pick_best_orders_crew import build_pick_best_orders_crew
from bots.crews.random_orders_crew import build_random_orders_crew
from bots.crews.tactical_crew import build_tactical_crew
from bots.tools.get_tactical_order_bundle import GetTacticalOrderBundleTool
from bots.tools.send_message import SendGlobalMessageTool

CREW_RANDOM = "random_orders_crew"
CREW_PICK_BEST = "pick_best_orders_crew"
CREW_EZRA = "ezra_crew"
CREW_TACTICAL = "tactical_crew"
NOCREW_RANDOM = "nocrew_random"
DEFAULT_CREW = CREW_RANDOM


ToolFactory = Callable[[Any], List[Any]]
CrewBuilder = Callable[..., Any]


def _empty_tools(_: Any) -> List[Any]:
    return []


def _tactical_tools(game: Any) -> List[Any]:
    return [GetTacticalOrderBundleTool(game=game)]


@dataclass(frozen=True)
class CrewAdapter:
    """Adapter for building a crew with consistent hooks."""

    name: str
    builder: CrewBuilder
    tools_factory: ToolFactory = _empty_tools
    supports_taunt: bool = False

    def build(
        self,
        *,
        game: Any,
        power_name: str,
        message_queue: Optional[List[str]] = None,
        taunt_target: Optional[str] = None,
    ) -> Any:
        tools = self.tools_factory(game)

        if self.supports_taunt:
            taunt_tools = []
            if taunt_target and message_queue is not None:
                taunt_tools = [
                    SendGlobalMessageTool(
                        power_name=power_name,
                        message_queue=message_queue,
                    )
                ]
            return self.builder(tools=tools, taunt_tools=taunt_tools)

        return self.builder(tools=tools)


_CREW_ADAPTERS: Dict[str, CrewAdapter] = {
    CREW_RANDOM: CrewAdapter(
        name=CREW_RANDOM,
        builder=build_random_orders_crew,
    ),
    CREW_PICK_BEST: CrewAdapter(
        name=CREW_PICK_BEST,
        builder=build_pick_best_orders_crew,
        supports_taunt=True,
    ),
    CREW_EZRA: CrewAdapter(
        name=CREW_EZRA,
        builder=build_ezra_crew,
        supports_taunt=True,
    ),
    CREW_TACTICAL: CrewAdapter(
        name=CREW_TACTICAL,
        builder=build_tactical_crew,
        tools_factory=_tactical_tools,
    ),
}


def get_crew_adapter(crew_name: str) -> CrewAdapter:
    """Resolve a crew adapter, falling back to the default adapter."""
    return _CREW_ADAPTERS.get(crew_name, _CREW_ADAPTERS[DEFAULT_CREW])


def build_crew(
    crew_name: str,
    *,
    game: Any,
    power_name: str,
    message_queue: Optional[List[str]] = None,
    taunt_target: Optional[str] = None,
) -> Any:
    """Build a crew instance via the adapter registry."""
    adapter = get_crew_adapter(crew_name)
    return adapter.build(
        game=game,
        power_name=power_name,
        message_queue=message_queue,
        taunt_target=taunt_target,
    )


def is_no_crew_strategy(crew_name: str) -> bool:
    return crew_name == NOCREW_RANDOM
