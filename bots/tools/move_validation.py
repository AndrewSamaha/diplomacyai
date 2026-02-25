import json
from collections import defaultdict
from typing import Any, Dict, List, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr


def _normalize_order_text(order: str) -> str:
    return " ".join(order.upper().strip().split())


def _base_loc(loc: str) -> str:
    return loc.upper()[:3]


def _extract_order_location(order: str, fallback_location: Optional[str] = None) -> Optional[str]:
    tokens = order.upper().split()
    if not tokens:
        return _base_loc(fallback_location) if fallback_location else None
    if tokens[0] == "WAIVE":
        return "WAIVE"
    if len(tokens) >= 2 and tokens[0] in {"A", "F"}:
        return _base_loc(tokens[1])
    return _base_loc(fallback_location) if fallback_location else None


def validate_orders(
    game: Any,
    power_name: str,
    orders: List[str],
    require_complete: bool = False,
) -> Dict[str, Any]:
    power_name = power_name.upper()
    orderable_locations = game.get_orderable_locations(power_name)
    possible_orders = game.get_all_possible_orders()

    legal_by_loc: Dict[str, List[str]] = {}
    legal_norm_to_canonical: Dict[str, str] = {}
    legal_by_unit_loc: Dict[str, List[str]] = defaultdict(list)

    for loc in orderable_locations:
        legal_orders = list(possible_orders.get(loc, []))
        legal_by_loc[loc] = legal_orders
        for legal_order in legal_orders:
            norm = _normalize_order_text(legal_order)
            legal_norm_to_canonical.setdefault(norm, legal_order)
            unit_loc = _extract_order_location(legal_order, fallback_location=loc)
            if unit_loc:
                legal_by_unit_loc[unit_loc].append(legal_order)

    errors: List[Dict[str, Any]] = []
    normalized_orders: List[str] = []
    seen_locations: Dict[str, str] = {}
    duplicate_locations: List[str] = []

    if not isinstance(orders, list):
        return {
            "valid": False,
            "normalized_orders": [],
            "errors": [
                {
                    "code": "invalid_orders_format",
                    "message": "Orders must be a list of strings.",
                }
            ],
            "missing_locations": [],
            "duplicate_locations": [],
            "summary": "Orders format is invalid.",
        }

    for raw_order in orders:
        if not isinstance(raw_order, str) or not raw_order.strip():
            errors.append(
                {
                    "code": "invalid_order_entry",
                    "order": raw_order,
                    "message": "Each order must be a non-empty string.",
                }
            )
            continue

        norm = _normalize_order_text(raw_order)
        canonical = legal_norm_to_canonical.get(norm)
        if canonical is None:
            loc_guess = _extract_order_location(raw_order)
            hints = legal_by_unit_loc.get(loc_guess, [])[:5] if loc_guess else []
            errors.append(
                {
                    "code": "illegal_order",
                    "order": raw_order,
                    "location": loc_guess,
                    "message": "Order is not legal for this power in the current phase.",
                    "hint": hints,
                }
            )
            continue

        canonical_loc = _extract_order_location(canonical)
        if canonical_loc and canonical_loc != "WAIVE":
            if canonical_loc in seen_locations:
                duplicate_locations.append(canonical_loc)
                errors.append(
                    {
                        "code": "duplicate_location_order",
                        "order": raw_order,
                        "location": canonical_loc,
                        "message": "Multiple orders were provided for the same unit/location.",
                    }
                )
                continue
            seen_locations[canonical_loc] = canonical

        normalized_orders.append(canonical)

    required_locations = {_base_loc(loc) for loc in orderable_locations}
    missing_locations = sorted(required_locations - set(seen_locations.keys()))
    if require_complete and missing_locations:
        errors.append(
            {
                "code": "missing_required_orders",
                "message": "No orders were provided for some orderable locations.",
                "missing_locations": missing_locations,
            }
        )

    duplicate_locations = sorted(set(duplicate_locations))

    valid = len(errors) == 0
    summary = (
        "All provided orders are legal."
        if valid
        else f"Validation failed with {len(errors)} error(s)."
    )
    return {
        "valid": valid,
        "normalized_orders": normalized_orders,
        "errors": errors,
        "missing_locations": missing_locations,
        "duplicate_locations": duplicate_locations,
        "summary": summary,
    }


class MoveValidationInput(BaseModel):
    power_name: str = Field(..., description="Power name to validate orders for.")
    orders: List[str] = Field(..., description="Proposed orders to validate.")
    require_complete: bool = Field(
        False,
        description="If true, require one order for each orderable location.",
    )


class MoveValidationTool(BaseTool):
    name: str = "move_validation"
    description: str = (
        "Validate proposed orders against current legal moves and return structured errors/hints."
    )
    args_schema: Type[BaseModel] = MoveValidationInput

    _game: Any = PrivateAttr()

    def __init__(self, game):
        super().__init__()
        self._game = game

    def _run(self, power_name: str, orders: List[str], require_complete: bool = False) -> str:
        report = validate_orders(
            game=self._game,
            power_name=power_name,
            orders=orders,
            require_complete=require_complete,
        )
        return json.dumps(report)
