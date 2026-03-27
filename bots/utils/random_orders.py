"""Utility for generating random legal orders without using an agent."""
import random
from typing import List


def _is_hold_order(order: str) -> bool:
    return bool(order) and order.split()[-1] == "H"


def _get_orders(game, power_name: str, *, prefer_hold: bool) -> List[str]:
    """Generate legal orders for a power, optionally preferring holds."""
    orderable_locations = game.get_orderable_locations(power_name)
    possible_orders = game.get_all_possible_orders()

    orders = []
    for location in orderable_locations:
        options = possible_orders.get(location, [])
        if not options:
            continue

        if prefer_hold:
            hold_order = next((order for order in options if _is_hold_order(order)), None)
            if hold_order is not None:
                orders.append(hold_order)
                continue

        orders.append(random.choice(options))

    return orders


def get_random_orders(game, power_name: str) -> List[str]:
    """
    Generate random legal orders for a power.
    
    Args:
        game: The game object
        power_name: The power to generate orders for
    
    Returns:
        A list of random legal orders for each orderable location.
    """
    return _get_orders(game, power_name, prefer_hold=False)


def get_hold_only_orders(game, power_name: str) -> List[str]:
    """
    Generate legal orders for a power, choosing HOLD when available.

    Args:
        game: The game object
        power_name: The power to generate orders for

    Returns:
        A list of legal orders for each orderable location, preferring HOLD.
    """
    return _get_orders(game, power_name, prefer_hold=True)
