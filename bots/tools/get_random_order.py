import json
import random
from typing import List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class PossibleOrdersItem(BaseModel):
    location: str = Field(..., description="Orderable location name.")
    orders: List[str] = Field(..., description="Legal orders for that location.")


class GetRandomOrderInput(BaseModel):
    orderable_locations: List[str] = Field(
        ...,
        description="Locations that require orders for the current power.",
    )
    possible_orders: List[PossibleOrdersItem] = Field(
        ...,
        description="List of legal orders per location.",
    )


class GetRandomOrderTool(BaseTool):
    name: str = "get_random_order"
    description: str = "Selects a random legal order for each orderable location."
    args_schema: Type[BaseModel] = GetRandomOrderInput

    def _run(self, orderable_locations: List[str], possible_orders: List[PossibleOrdersItem]) -> str:
        possible_map = {item.location: item.orders for item in possible_orders}
        orders: List[str] = []
        for location in orderable_locations:
            options = possible_map.get(location, [])
            if options:
                orders.append(random.choice(options))
        return json.dumps({"orders": orders})
