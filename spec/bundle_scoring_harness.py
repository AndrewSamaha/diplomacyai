"""Utilities for replaying saved games at a target phase for bundle-scoring work."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

from bots.utils.tactical.select_best_order_bundle import select_best_order_bundle
from diplomacy.engine.game import Game
from diplomacy.utils import export, strings
from diplomacy.utils.game_phase_data import GamePhaseData


@dataclass(frozen=True)
class BundleSearchInputs:
    """Prepared inputs for tactical bundle-search evaluation."""

    game: Game
    phase_name: str
    power_name: str
    orderable_locations: list[str]
    possible_orders: list[dict[str, object]]
    units_by_power: dict[str, list[str]]
    centers_by_power: dict[str, list[str]]
    loc_abut: dict[str, list[str]]
    supply_centers: list[str]


def load_saved_game(saved_game_path: str | Path) -> dict[str, Any]:
    """Read a saved game JSON file from disk."""
    saved_game_file = Path(saved_game_path)
    with saved_game_file.open('r', encoding='utf-8') as stream:
        return json.load(stream)


def list_saved_game_phases(saved_game_path: str | Path) -> list[str]:
    """Return available phase names for a saved game file."""
    saved_game = load_saved_game(saved_game_path)
    return [phase.name for phase in _load_phase_history(saved_game)]


def load_game_at_phase(saved_game_path: str | Path, phase_name: str) -> Game:
    """Load a saved game and materialize a Game positioned at the requested phase."""
    saved_game = load_saved_game(saved_game_path)
    phases = _load_phase_history(saved_game)
    target_index = _find_phase_index(phases, phase_name)
    materialized_game = _build_game_shell(saved_game)
    materialized_game.set_phase_data(phases[: target_index + 1], clear_history=True)
    return materialized_game


def load_bundle_search_inputs(
    saved_game_path: str | Path,
    phase_name: str,
    power_name: str,
) -> BundleSearchInputs:
    """Build bundle-search inputs from a saved game at a specific phase."""
    game = load_game_at_phase(saved_game_path, phase_name)
    normalized_power = power_name.upper()
    available_powers = sorted(power.name for power in game.powers.values())
    if normalized_power not in available_powers:
        raise ValueError(f'Unknown power {normalized_power!r}. Available powers: {available_powers}')

    orderable_locations = list(game.get_orderable_locations(normalized_power))
    possible_orders_by_loc = game.get_all_possible_orders()
    possible_orders = [
        {'location': location, 'orders': possible_orders_by_loc.get(location, [])}
        for location in orderable_locations
    ]
    units_by_power = {power.name: list(power.units) for power in game.powers.values()}
    centers_by_power = {power.name: list(power.centers) for power in game.powers.values()}

    return BundleSearchInputs(
        game=game,
        phase_name=phase_name,
        power_name=normalized_power,
        orderable_locations=orderable_locations,
        possible_orders=possible_orders,
        units_by_power=units_by_power,
        centers_by_power=centers_by_power,
        loc_abut=game.map.loc_abut,
        supply_centers=list(getattr(game.map, 'scs', [])),
    )


def run_bundle_search_from_saved_game(
    saved_game_path: str | Path,
    phase_name: str,
    power_name: str,
    *,
    beam_width: int = 32,
    include_non_moves: bool = True,
) -> dict[str, object]:
    """Run the bundle search from a saved game snapshot."""
    inputs = load_bundle_search_inputs(saved_game_path, phase_name, power_name)
    return select_best_order_bundle(
        power_name=inputs.power_name,
        possible_orders=inputs.possible_orders,
        units_by_power=inputs.units_by_power,
        centers_by_power=inputs.centers_by_power,
        loc_abut=inputs.loc_abut,
        supply_centers=inputs.supply_centers,
        beam_width=beam_width,
        include_non_moves=include_non_moves,
    )


def _build_game_shell(saved_game: dict[str, Any]) -> Game:
    if 'phases' in saved_game:
        return Game(
            game_id=saved_game.get('id'),
            map_name=saved_game.get('map', 'standard'),
            rules=saved_game.get('rules', []),
        )
    if strings.GAME_ID in saved_game or strings.MAP_NAME in saved_game:
        return Game(
            game_id=saved_game.get(strings.GAME_ID),
            map_name=saved_game.get(strings.MAP_NAME, 'standard'),
            rules=saved_game.get(strings.RULES, []),
        )
    raise ValueError('Unsupported saved game format.')


def _load_phase_history(saved_game: dict[str, Any]) -> list[GamePhaseData]:
    if 'phases' in saved_game:
        return [GamePhaseData.from_dict(phase_dict) for phase_dict in saved_game.get('phases', [])]
    if strings.STATE_HISTORY in saved_game:
        game = Game.from_dict(saved_game)
        phases = Game.get_phase_history(game)
        phases.append(Game.get_phase_data(game))
        return phases
    raise ValueError('Unsupported saved game format.')


def _find_phase_index(phases: list[GamePhaseData], phase_name: str) -> int:
    for index, phase in enumerate(phases):
        if phase.name == phase_name:
            return index
    available_phases = [phase.name for phase in phases]
    raise ValueError(f'Phase {phase_name!r} not found. Available phases: {available_phases}')
