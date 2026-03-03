import json
from typing import Any, Dict, List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr


class GameSnapshotInput(BaseModel):
    """No-arg tool input."""


class GameSnapshotTool(BaseTool):
    name: str = "get_game_snapshot"
    description: str = (
        "Return a minimal game snapshot including phase, orderable locations, "
        "possible orders, units, and centers."
    )
    args_schema: Type[BaseModel] = GameSnapshotInput

    _game: Any = PrivateAttr()
    _power_name: str = PrivateAttr()

    def __init__(self, game, power_name: str):
        super().__init__()
        self._game = game
        self._power_name = power_name

    def _run(self) -> str:
        game = self._game
        power_name = self._power_name

        orderable_locations = game.get_orderable_locations(power_name)
        possible_orders = game.get_all_possible_orders()
        possible_orders_list = [
            {"location": loc, "orders": possible_orders.get(loc, [])}
            for loc in orderable_locations
        ]

        units_by_power: Dict[str, List[str]] = {
            power.name: list(power.units) for power in game.powers.values()
        }
        centers_by_power: Dict[str, List[str]] = {
            power.name: list(power.centers) for power in game.powers.values()
        }

        snapshot = {
            "phase": game.get_current_phase(),
            "power_name": power_name,
            "orderable_locations": orderable_locations,
            "possible_orders": possible_orders_list,
            "units_by_power": units_by_power,
            "centers_by_power": centers_by_power,
        }
        return json.dumps(snapshot)
