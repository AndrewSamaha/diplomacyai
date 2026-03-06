import json
from typing import Any, Dict, List, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from bots.utils.tactical import annotate_possible_orders

AVAILABLE_ANNOTATIONS = [
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
]


class TacticalMoveAnnotationsInput(BaseModel):
    power_name: str = Field(..., description="Power name to query possible move annotations for.")
    annotations: Optional[List[str]] = Field(
        default=None,
        description=(
            "Optional subset of annotations to include in each move's metrics. "
            f"Allowed values: {', '.join(AVAILABLE_ANNOTATIONS)}"
        ),
    )
    include_non_moves: bool = Field(
        default=False,
        description="If true, include non-move orders (H/S/C/B/D) in the response.",
    )


class GetTacticalMoveAnnotationsTool(BaseTool):
    name: str = "get_tactical_move_annotations"
    description: str = (
        "Return legal possible orders for a power with deterministic tactical annotations for move orders. "
        "LLM can choose which annotation fields to include via `annotations`."
    )
    args_schema: Type[BaseModel] = TacticalMoveAnnotationsInput

    _game: Any = PrivateAttr()

    def __init__(self, game):
        super().__init__()
        self._game = game

    @staticmethod
    def _selected_annotations(requested: Optional[List[str]]) -> tuple[List[str], Optional[str]]:
        if not requested:
            return list(AVAILABLE_ANNOTATIONS), None
        unknown = [name for name in requested if name not in AVAILABLE_ANNOTATIONS]
        if unknown:
            return [], f"Unknown annotations requested: {unknown}"
        return requested, None

    def _run(
        self,
        power_name: str,
        annotations: Optional[List[str]] = None,
        include_non_moves: bool = False,
    ) -> str:
        selected_annotations, error = self._selected_annotations(annotations)
        normalized_power = power_name.upper()

        available_powers = [power.name for power in self._game.powers.values()]
        if normalized_power not in available_powers:
            return json.dumps(
                {
                    "error": f"Unknown power requested: {normalized_power}",
                    "available_powers": available_powers,
                    "available_annotations": AVAILABLE_ANNOTATIONS,
                }
            )

        if error:
            return json.dumps(
                {
                    "error": error,
                    "available_powers": available_powers,
                    "available_annotations": AVAILABLE_ANNOTATIONS,
                }
            )

        orderable_locations = self._game.get_orderable_locations(normalized_power)
        possible_orders_by_loc = self._game.get_all_possible_orders()

        possible_orders = [
            {"location": loc, "orders": possible_orders_by_loc.get(loc, [])}
            for loc in orderable_locations
        ]

        units_by_power: Dict[str, List[str]] = {
            power.name: list(power.units) for power in self._game.powers.values()
        }
        centers_by_power: Dict[str, List[str]] = {
            power.name: list(power.centers) for power in self._game.powers.values()
        }

        annotations_full = annotate_possible_orders(
            power_name=normalized_power,
            possible_orders=possible_orders,
            units_by_power=units_by_power,
            centers_by_power=centers_by_power,
            loc_abut=self._game.map.loc_abut,
        )

        output_orders: List[Dict[str, Any]] = []
        for item in annotations_full:
            if not include_non_moves and not item["is_move"]:
                continue
            metrics = item["metrics"]
            if metrics is not None:
                metrics = {name: metrics[name] for name in selected_annotations}
            output_orders.append(
                {
                    "order": item["order"],
                    "location": item["location"],
                    "destination": item["destination"],
                    "is_move": item["is_move"],
                    "move_rank": item["move_rank"],
                    "metrics": metrics,
                }
            )

        return json.dumps(
            {
                "power_name": normalized_power,
                "phase": self._game.get_current_phase(),
                "orderable_locations": orderable_locations,
                "selected_annotations": selected_annotations,
                "available_annotations": AVAILABLE_ANNOTATIONS,
                "possible_moves": output_orders,
            }
        )
