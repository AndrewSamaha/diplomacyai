"""Build center ownership lookup."""

from bots.utils.tactical.base_location import base_location


def build_center_owner(centers_by_power: dict[str, list[str]]) -> dict[str, str]:
    """Return base center location -> owning power name."""
    owner_by_center: dict[str, str] = {}
    for power_name, centers in centers_by_power.items():
        normalized_power = str(power_name).upper()
        for center in centers:
            owner_by_center[base_location(center)] = normalized_power
    return owner_by_center
