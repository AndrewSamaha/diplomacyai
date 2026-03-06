"""Build normalized unit locations by power."""

from bots.utils.tactical.base_location import base_location


def build_units_by_power(units_by_power: dict[str, list[str]]) -> dict[str, set[str]]:
    """Return power->set(base location) from raw unit strings."""
    parsed: dict[str, set[str]] = {}
    for power_name, units in units_by_power.items():
        normalized_power = str(power_name).upper()
        parsed.setdefault(normalized_power, set())
        for unit in units:
            parts = str(unit).lstrip("*").split()
            if len(parts) >= 2:
                parsed[normalized_power].add(base_location(parts[1]))
    return parsed
