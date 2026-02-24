import json
import random
from typing import Any, List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class PossibleOrdersItem(BaseModel):
    location: str = Field(..., description="Orderable location name.")
    orders: List[str] = Field(..., description="Legal orders for that location.")


class GetRandomOrderCandidatesInput(BaseModel):
    orderable_locations: List[str] = Field(
        ...,
        description="Locations that require orders for the current power.",
    )
    possible_orders: List[PossibleOrdersItem] = Field(
        ...,
        description="List of legal orders per location.",
    )
    n_candidates: int = Field(
        10,
        description="Number of random candidate order sets to generate.",
    )


class GetRandomOrderCandidatesTool(BaseTool):
    name: str = "get_random_order_candidates"
    description: str = "Generate multiple random legal order sets."
    args_schema: Type[BaseModel] = GetRandomOrderCandidatesInput

    def _run(
        self,
        orderable_locations: List[str],
        possible_orders: List[Any],
        n_candidates: int = 10,
    ) -> str:
        possible_map = {}
        for item in possible_orders:
            if isinstance(item, dict):
                location = item.get("location")
                orders = item.get("orders", [])
            else:
                location = getattr(item, "location", None)
                orders = getattr(item, "orders", [])
            if location:
                possible_map[location] = orders

        candidates: List[List[str]] = []
        for _ in range(max(1, n_candidates)):
            orders: List[str] = []
            for location in orderable_locations:
                options = possible_map.get(location, [])
                if options:
                    orders.append(random.choice(options))
            candidates.append(orders)

        return json.dumps({"candidates": candidates})
