"""Utility for generating random legal orders without using an agent."""
import random
from typing import Dict, List


def get_random_orders(game, power_name: str) -> List[str]:
    """
    Generate random legal orders for a power.
    
    Args:
        game: The game object
        power_name: The power to generate orders for
    
    Returns:
        A list of random legal orders for each orderable location.
    """
    orderable_locations = game.get_orderable_locations(power_name)
    possible_orders = game.get_all_possible_orders()
    
    orders = []
    for location in orderable_locations:
        options = possible_orders.get(location, [])
        if options:
            orders.append(random.choice(options))
    
    return orders
