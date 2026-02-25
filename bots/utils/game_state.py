"""Utilities for extracting game state information."""
from typing import Dict, List, Any, Optional


def get_human_controlled_powers(game) -> List[str]:
    """Return a list of power names that are controlled by humans (not dummy/bot)."""
    return [
        power_name
        for power_name in game.get_map_power_names()
        if game.is_controlled(power_name)
    ]


def get_dummy_powers(game) -> List[str]:
    """Return a list of power names that are not controlled (dummy)."""
    return list(game.get_dummy_power_names())


def get_game_summary(game, power_name: str) -> Dict[str, Any]:
    """
    Build a summary of the current game state useful for agent context.
    
    Returns a dict with:
    - phase: current game phase
    - power_name: the power we're playing as
    - human_controlled_powers: list of human-controlled power names
    - dummy_powers: list of uncontrolled power names
    - units_by_power: dict mapping power name to list of units
    - centers_by_power: dict mapping power name to list of supply centers
    - center_counts: dict mapping power name to number of centers
    """
    human_powers = get_human_controlled_powers(game)
    dummy_powers = get_dummy_powers(game)
    
    units_by_power = {
        power.name: list(power.units) for power in game.powers.values()
    }
    centers_by_power = {
        power.name: list(power.centers) for power in game.powers.values()
    }
    center_counts = {
        power.name: len(power.centers) for power in game.powers.values()
    }
    
    return {
        "phase": game.get_current_phase(),
        "power_name": power_name,
        "human_controlled_powers": human_powers,
        "dummy_powers": dummy_powers,
        "units_by_power": units_by_power,
        "centers_by_power": centers_by_power,
        "center_counts": center_counts,
    }


def get_recent_messages(
    game,
    limit: int = 20,
    include_history: bool = True,
    filter_power: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Get recent messages from the game.
    
    Args:
        game: The game object
        limit: Maximum number of messages to return
        include_history: If True, include messages from previous phases
        filter_power: If set, only include messages where this power is sender or recipient
    
    Returns:
        List of message dicts with keys: sender, recipient, phase, message
        Messages are ordered from oldest to newest.
    """
    messages = []
    
    if include_history and hasattr(game, 'message_history') and game.message_history:
        for phase, phase_messages in game.message_history.items():
            if phase_messages:
                for msg in phase_messages.values():
                    messages.append({
                        "sender": msg.sender,
                        "recipient": msg.recipient,
                        "phase": msg.phase,
                        "message": msg.message,
                    })
    
    if hasattr(game, 'messages') and game.messages:
        for msg in game.messages.values():
            messages.append({
                "sender": msg.sender,
                "recipient": msg.recipient,
                "phase": msg.phase,
                "message": msg.message,
            })
    
    if filter_power:
        messages = [
            m for m in messages
            if m["sender"] == filter_power 
            or m["recipient"] == filter_power 
            or m["recipient"] == "GLOBAL"
        ]
    
    return messages[-limit:]


def format_messages_for_context(messages: List[Dict[str, str]]) -> str:
    """
    Format messages into a readable string for agent context.
    
    Args:
        messages: List of message dicts from get_recent_messages()
    
    Returns:
        A formatted string representation of the messages.
    """
    if not messages:
        return "No messages yet."
    
    lines = []
    for msg in messages:
        recipient = msg["recipient"]
        if recipient == "GLOBAL":
            recipient = "ALL"
        lines.append(f"[{msg['phase']}] {msg['sender']} -> {recipient}: {msg['message']}")
    
    return "\n".join(lines)
