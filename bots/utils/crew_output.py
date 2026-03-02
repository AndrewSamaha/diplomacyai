"""Helpers for normalizing CrewAI outputs."""

import json
from typing import Any


def extract_orders(result: Any):
    """Extract orders list from a CrewAI result."""
    raw = getattr(result, "raw", result)
    if isinstance(raw, dict):
        data = raw
    else:
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None
    if isinstance(data, dict) and "orders" in data:
        return data["orders"]
    if isinstance(data, list):
        return data
    return None


def serialize_for_trace(value: Any):
    """Return a JSON-serializable payload for trace output."""
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return str(value)

