import json
from typing import Any, Dict, List, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from bots.tools.get_tactical_move_annotations import AVAILABLE_ANNOTATIONS
from bots.utils.tactical import select_best_order_bundle


class TacticalOrderBundleInput(BaseModel):
    power_name: str = Field(..., description="Power name to select a full order bundle for.")
    annotations: Optional[List[str]] = Field(
        default=None,
        description=(
            "Optional subset of tactical annotations selected by the planner. "
            "Used for planning metadata in output."
        ),
    )
    include_non_moves: bool = Field(
        default=True,
        description="If true, include non-move orders in candidate bundles.",
    )
    beam_width: int = Field(
        default=32,
        ge=1,
        le=512,
        description="Beam width for deterministic bundle search.",
    )


class GetTacticalOrderBundleTool(BaseTool):
    name: str = "get_tactical_order_bundle"
    description: str = (
        "Return one deterministic best full order bundle (one legal order per orderable location) "
        "using beam-search tactical scoring across all units."
    )
    args_schema: Type[BaseModel] = TacticalOrderBundleInput

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
        include_non_moves: bool = True,
        beam_width: int = 32,
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

        bundle = select_best_order_bundle(
            power_name=normalized_power,
            possible_orders=possible_orders,
            units_by_power=units_by_power,
            centers_by_power=centers_by_power,
            loc_abut=self._game.map.loc_abut,
            supply_centers=list(getattr(self._game.map, "scs", [])),
            beam_width=beam_width,
            include_non_moves=include_non_moves,
        )

        return json.dumps(
            {
                "power_name": normalized_power,
                "phase": self._game.get_current_phase(),
                "orderable_locations": orderable_locations,
                "selected_annotations": selected_annotations,
                "available_annotations": AVAILABLE_ANNOTATIONS,
                "beam_width": int(beam_width),
                "recommended_orders": bundle["recommended_orders"],
                "resolved_orders": bundle["resolved_orders"],
                "resolution_metadata": bundle["resolution_metadata"],
                "bundle_score": bundle["bundle_score"],
                "score_breakdown": bundle["score_breakdown"],
                "evaluated_bundles": bundle["evaluated_bundles"],
            }
        )
