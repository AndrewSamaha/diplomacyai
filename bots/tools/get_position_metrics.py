import json
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

METRIC_BUILD_PRESSURE = "build_pressure"
METRIC_GROWTH_TREND = "growth_trend"
METRIC_CENTER_QUALITY = "center_quality"
METRIC_FRONTLINE_EXPOSURE = "frontline_exposure"
METRIC_DEFENSIVE_COVERAGE = "defensive_coverage"
METRIC_OFFENSIVE_REACH = "offensive_reach"
METRIC_SUPPORT_NETWORK_STRENGTH = "support_network_strength"
METRIC_MOBILITY_TEMPO = "mobility_tempo"
METRIC_POSITIONAL_COHESION = "positional_cohesion"
METRIC_CONFLICT_LOAD = "conflict_load"
METRIC_ORDER_EFFICIENCY = "order_efficiency"
METRIC_INFLUENCE_FOOTPRINT = "influence_footprint"

ALL_METRICS = [
    METRIC_BUILD_PRESSURE,
    METRIC_GROWTH_TREND,
    METRIC_CENTER_QUALITY,
    METRIC_FRONTLINE_EXPOSURE,
    METRIC_DEFENSIVE_COVERAGE,
    METRIC_OFFENSIVE_REACH,
    METRIC_SUPPORT_NETWORK_STRENGTH,
    METRIC_MOBILITY_TEMPO,
    METRIC_POSITIONAL_COHESION,
    METRIC_CONFLICT_LOAD,
    METRIC_ORDER_EFFICIENCY,
    METRIC_INFLUENCE_FOOTPRINT,
]


class PositionMetricsInput(BaseModel):
    metrics: Optional[List[str]] = Field(
        default=None,
        description=(
            "Optional subset of metrics to return. "
            f"Allowed values: {', '.join(ALL_METRICS)}"
        ),
    )
    powers: Optional[List[str]] = Field(
        default=None,
        description="Optional subset of power names to return metrics for.",
    )


class GetPositionMetricsTool(BaseTool):
    name: str = "get_position_metrics"
    description: str = (
        "Return per-power position strength metrics. Can return all 12 metrics in one call "
        "or only a requested subset via `metrics` and/or `powers`."
    )
    args_schema: Type[BaseModel] = PositionMetricsInput

    _game: Any = PrivateAttr()

    def __init__(self, game):
        super().__init__()
        self._game = game

    @staticmethod
    def _base_loc(loc: str) -> str:
        return loc.upper()[:3]

    @staticmethod
    def _unit_loc(unit: str) -> str:
        unit = unit.lstrip("*")
        parts = unit.split()
        if len(parts) >= 2:
            return parts[1].upper()
        return ""

    @staticmethod
    def _order_dest(order: str) -> Optional[str]:
        if " - " not in order:
            return None
        return order.rsplit(" - ", 1)[1].split()[0].upper()

    @staticmethod
    def _order_support_dest(order: str) -> Optional[str]:
        if " S " not in order:
            return None
        if " - " in order:
            return GetPositionMetricsTool._order_dest(order)
        parts = order.split()
        return parts[-1].upper() if parts else None

    @staticmethod
    def _order_unit(order: str) -> Optional[str]:
        parts = order.split()
        if len(parts) < 2:
            return None
        return f"{parts[0]} {parts[1]}".upper()

    def _selected_powers(self, requested: Optional[List[str]]) -> Tuple[List[str], Optional[str]]:
        game_powers = [power.name for power in self._game.powers.values()]
        if not requested:
            return game_powers, None
        requested_set = [power.upper() for power in requested]
        unknown = [power for power in requested_set if power not in game_powers]
        if unknown:
            return [], f"Unknown powers requested: {unknown}"
        return requested_set, None

    @staticmethod
    def _selected_metrics(requested: Optional[List[str]]) -> Tuple[List[str], Optional[str]]:
        if not requested:
            return list(ALL_METRICS), None
        unknown = [metric for metric in requested if metric not in ALL_METRICS]
        if unknown:
            return [], f"Unknown metrics requested: {unknown}"
        return requested, None

    def _move_support_stats(
        self, power_name: str, possible_orders_by_loc: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        orderable_locations = self._game.get_orderable_locations(power_name)
        legal_orders = 0
        move_orders = 0
        support_orders = 0
        move_dests: Set[str] = set()
        defend_targets: Set[str] = set()

        for loc in orderable_locations:
            for order in possible_orders_by_loc.get(loc, []):
                legal_orders += 1
                if " - " in order:
                    move_orders += 1
                    dest = self._order_dest(order)
                    if dest:
                        move_dests.add(self._base_loc(dest))
                        defend_targets.add(self._base_loc(dest))
                if " S " in order:
                    support_orders += 1
                    support_dest = self._order_support_dest(order)
                    if support_dest:
                        defend_targets.add(self._base_loc(support_dest))

        return {
            "orderable_locations": orderable_locations,
            "legal_orders": legal_orders,
            "move_orders": move_orders,
            "support_orders": support_orders,
            "move_dests": move_dests,
            "defend_targets": defend_targets,
        }

    def _unit_graph_components(self, unit_locs: List[str]) -> Tuple[int, float]:
        if not unit_locs:
            return 0, 0.0
        if len(unit_locs) == 1:
            return 1, 1.0

        map_obj = self._game.map
        nodes = list({loc.upper() for loc in unit_locs if loc})
        node_set = set(nodes)
        seen: Set[str] = set()
        components = 0
        largest = 0

        for start in nodes:
            if start in seen:
                continue
            components += 1
            size = 0
            queue = deque([start])
            seen.add(start)
            while queue:
                current = queue.popleft()
                size += 1
                current_base = self._base_loc(current)
                for neighbor in map_obj.abut_list(current_base, incl_no_coast=True):
                    neighbor_base = self._base_loc(neighbor)
                    if neighbor_base in node_set and neighbor_base not in seen:
                        seen.add(neighbor_base)
                        queue.append(neighbor_base)
            largest = max(largest, size)

        return components, largest / len(nodes)

    def _latest_historical_state(self) -> Optional[Dict[str, Any]]:
        history = self._game.state_history
        if not history:
            return None
        values = list(history.values())
        return values[-1] if values else None

    def _latest_phase_order_and_result(
        self,
    ) -> Tuple[Optional[Dict[str, List[str]]], Optional[Dict[str, List[str]]]]:
        if not self._game.order_history or not self._game.result_history:
            return None, None
        phase_keys = list(self._game.order_history.keys())
        if not phase_keys:
            return None, None
        latest_phase = phase_keys[-1]
        return self._game.order_history.get(latest_phase), self._game.result_history.get(latest_phase)

    def _run(self, metrics: Optional[List[str]] = None, powers: Optional[List[str]] = None) -> str:
        selected_metrics, metrics_error = self._selected_metrics(metrics)
        selected_powers, powers_error = self._selected_powers(powers)
        if metrics_error or powers_error:
            return json.dumps(
                {
                    "error": metrics_error or powers_error,
                    "available_metrics": ALL_METRICS,
                    "available_powers": [power.name for power in self._game.powers.values()],
                }
            )

        game = self._game
        map_obj = game.map

        units_by_power: Dict[str, List[str]] = {
            power: [self._unit_loc(unit) for unit in game.get_units(power) if self._unit_loc(unit)]
            for power in selected_powers
        }
        centers_by_power: Dict[str, List[str]] = {
            power: [center.upper() for center in game.get_centers(power)]
            for power in selected_powers
        }
        influence_by_power: Dict[str, List[str]] = {
            power: [loc.upper() for loc in game.get_power(power).influence]
            for power in selected_powers
        }
        homes_by_power: Dict[str, Set[str]] = {
            power: {loc.upper() for loc in game.get_power(power).homes}
            for power in selected_powers
        }

        all_centers_by_power = {
            power.name: [center.upper() for center in game.get_centers(power.name)]
            for power in game.powers.values()
        }

        center_owner: Dict[str, str] = {}
        for owner, owned_centers in all_centers_by_power.items():
            for center in owned_centers:
                center_owner[center] = owner

        enemy_home_centers: Dict[str, Set[str]] = {}
        for power in selected_powers:
            enemy_homes = set()
            for other_power in game.powers.values():
                if other_power.name == power:
                    continue
                enemy_homes |= {loc.upper() for loc in other_power.homes}
            enemy_home_centers[power] = enemy_homes

        possible_orders_by_loc = game.get_all_possible_orders()
        stats_by_power = {
            power: self._move_support_stats(power, possible_orders_by_loc)
            for power in selected_powers
        }

        attack_dests_by_power: Dict[str, Set[str]] = {
            power: set(stats["move_dests"]) for power, stats in stats_by_power.items()
        }

        contested_by_dest: Dict[str, Set[str]] = defaultdict(set)
        for power, dests in attack_dests_by_power.items():
            for dest in dests:
                contested_by_dest[dest].add(power)

        prev_state = self._latest_historical_state()
        prev_counts = {}
        if prev_state:
            for power in selected_powers:
                prev_units = prev_state.get("units", {}).get(power, [])
                prev_centers = prev_state.get("centers", {}).get(power, [])
                prev_influence = prev_state.get("influence", {}).get(power, [])
                prev_counts[power] = {
                    "units": len(prev_units),
                    "centers": len(prev_centers),
                    "territories": len(prev_influence),
                }

        latest_orders_by_power, latest_results_by_unit = self._latest_phase_order_and_result()

        metrics_out: Dict[str, Dict[str, Any]] = {metric: {} for metric in selected_metrics}

        for power in selected_powers:
            unit_locs = units_by_power[power]
            center_locs = centers_by_power[power]
            influence_locs = influence_by_power[power]
            unit_count = len(unit_locs)
            center_count = len(center_locs)
            territory_count = len(influence_locs)
            stats = stats_by_power[power]

            if METRIC_BUILD_PRESSURE in selected_metrics:
                build_pressure = center_count - unit_count
                metrics_out[METRIC_BUILD_PRESSURE][power] = {
                    "supply_centers": center_count,
                    "units": unit_count,
                    "territories": territory_count,
                    "build_pressure": build_pressure,
                }

            if METRIC_GROWTH_TREND in selected_metrics:
                prev = prev_counts.get(power)
                if prev:
                    metrics_out[METRIC_GROWTH_TREND][power] = {
                        "delta_supply_centers": center_count - prev["centers"],
                        "delta_units": unit_count - prev["units"],
                        "delta_territories": territory_count - prev["territories"],
                    }
                else:
                    metrics_out[METRIC_GROWTH_TREND][power] = {
                        "delta_supply_centers": None,
                        "delta_units": None,
                        "delta_territories": None,
                    }

            if METRIC_CENTER_QUALITY in selected_metrics:
                own_homes = homes_by_power[power]
                own_centers_set = set(center_locs)
                metrics_out[METRIC_CENTER_QUALITY][power] = {
                    "home_centers_held": len(own_centers_set & own_homes),
                    "enemy_home_centers_held": len(own_centers_set & enemy_home_centers[power]),
                }

            if METRIC_FRONTLINE_EXPOSURE in selected_metrics:
                enemy_attack_dests = set()
                for enemy_power, enemy_dests in attack_dests_by_power.items():
                    if enemy_power != power:
                        enemy_attack_dests |= enemy_dests
                exposed_units = sum(
                    1 for loc in unit_locs if self._base_loc(loc) in enemy_attack_dests
                )
                exposed_centers = sum(
                    1 for center in center_locs if self._base_loc(center) in enemy_attack_dests
                )
                metrics_out[METRIC_FRONTLINE_EXPOSURE][power] = {
                    "exposed_units": exposed_units,
                    "exposed_centers": exposed_centers,
                }

            if METRIC_DEFENSIVE_COVERAGE in selected_metrics:
                defended = set(stats["defend_targets"]) | {self._base_loc(loc) for loc in unit_locs}
                own_centers_set = {self._base_loc(center) for center in center_locs}
                covered = len(own_centers_set & defended)
                coverage_ratio = covered / len(own_centers_set) if own_centers_set else 0.0
                metrics_out[METRIC_DEFENSIVE_COVERAGE][power] = {
                    "covered_centers": covered,
                    "total_centers": len(own_centers_set),
                    "coverage_ratio": coverage_ratio,
                }

            if METRIC_OFFENSIVE_REACH in selected_metrics:
                enemy_centers = {
                    center
                    for center, owner in center_owner.items()
                    if owner != power
                }
                reachable_enemy_centers = {
                    dest for dest in stats["move_dests"] if dest in enemy_centers
                }
                metrics_out[METRIC_OFFENSIVE_REACH][power] = {
                    "reachable_enemy_centers": len(reachable_enemy_centers),
                    "enemy_centers_targeted": sorted(reachable_enemy_centers),
                }

            if METRIC_SUPPORT_NETWORK_STRENGTH in selected_metrics:
                orderable_count = max(1, len(stats["orderable_locations"]))
                metrics_out[METRIC_SUPPORT_NETWORK_STRENGTH][power] = {
                    "support_options": stats["support_orders"],
                    "support_options_per_orderable_unit": stats["support_orders"] / orderable_count,
                }

            if METRIC_MOBILITY_TEMPO in selected_metrics:
                mobility_base = max(1, len(stats["orderable_locations"]))
                metrics_out[METRIC_MOBILITY_TEMPO][power] = {
                    "legal_orders": stats["legal_orders"],
                    "move_options": stats["move_orders"],
                    "move_options_per_orderable_unit": stats["move_orders"] / mobility_base,
                }

            if METRIC_POSITIONAL_COHESION in selected_metrics:
                components, largest_ratio = self._unit_graph_components(unit_locs)
                metrics_out[METRIC_POSITIONAL_COHESION][power] = {
                    "connected_components": components,
                    "largest_component_ratio": largest_ratio,
                }

            if METRIC_CONFLICT_LOAD in selected_metrics:
                contested_provinces = [
                    dest
                    for dest, powers_on_dest in contested_by_dest.items()
                    if len(powers_on_dest) >= 2 and power in powers_on_dest
                ]
                enemy_pressure_count = 0
                own_pressure_targets = {self._base_loc(loc) for loc in unit_locs} | {
                    self._base_loc(center) for center in center_locs
                }
                for enemy_power, enemy_dests in attack_dests_by_power.items():
                    if enemy_power == power:
                        continue
                    if own_pressure_targets & enemy_dests:
                        enemy_pressure_count += 1
                metrics_out[METRIC_CONFLICT_LOAD][power] = {
                    "contested_provinces_involved": len(contested_provinces),
                    "enemy_fronts_pressuring": enemy_pressure_count,
                }

            if METRIC_ORDER_EFFICIENCY in selected_metrics:
                if not latest_orders_by_power or not latest_results_by_unit:
                    metrics_out[METRIC_ORDER_EFFICIENCY][power] = {
                        "order_count": None,
                        "success_rate": None,
                        "bounce_rate": None,
                        "dislodged_rate": None,
                    }
                else:
                    orders = latest_orders_by_power.get(power, [])
                    if not orders:
                        metrics_out[METRIC_ORDER_EFFICIENCY][power] = {
                            "order_count": 0,
                            "success_rate": None,
                            "bounce_rate": None,
                            "dislodged_rate": None,
                        }
                    else:
                        success_count = 0
                        bounce_count = 0
                        dislodged_count = 0
                        for order in orders:
                            unit = self._order_unit(order)
                            results = latest_results_by_unit.get(unit, []) if unit else []
                            codes = {str(code).lower() for code in results}
                            if "bounce" in codes:
                                bounce_count += 1
                            if "dislodged" in codes:
                                dislodged_count += 1
                            if not ({"void", "bounce", "no convoy"} & codes):
                                success_count += 1
                        total = len(orders)
                        metrics_out[METRIC_ORDER_EFFICIENCY][power] = {
                            "order_count": total,
                            "success_rate": success_count / total,
                            "bounce_rate": bounce_count / total,
                            "dislodged_rate": dislodged_count / total,
                        }

            if METRIC_INFLUENCE_FOOTPRINT in selected_metrics:
                adjacent = set()
                for loc in unit_locs:
                    for neighbor in map_obj.abut_list(self._base_loc(loc), incl_no_coast=True):
                        adjacent.add(self._base_loc(neighbor))
                metrics_out[METRIC_INFLUENCE_FOOTPRINT][power] = {
                    "influenced_territories": territory_count,
                    "adjacent_reachable_territories": len(adjacent),
                }

        return json.dumps(
            {
                "phase": game.get_current_phase(),
                "metrics_returned": selected_metrics,
                "powers_returned": selected_powers,
                "metrics": metrics_out,
            }
        )
