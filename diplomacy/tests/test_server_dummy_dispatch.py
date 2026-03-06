# ==============================================================================
# Copyright (C) 2019 - Philip Paquette
#
#  This program is free software: you can redistribute it and/or modify it under
#  the terms of the GNU Affero General Public License as published by the Free
#  Software Foundation, either version 3 of the License, or (at your option) any
#  later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
#  details.
#
#  You should have received a copy of the GNU Affero General Public License along
#  with this program.  If not, see <https://www.gnu.org/licenses/>.
# ==============================================================================
"""Unit tests for server dummy dispatch map allowlist behavior."""

from diplomacy.server.server import Server


class _DummyMap:
    def __init__(self, root_map):
        self.root_map = root_map


class _DummyServerGame:
    def __init__(self, game_id, root_map, dummy_powers, active=True, paused=False):
        self.game_id = game_id
        self.map = _DummyMap(root_map)
        self._dummy_powers = list(dummy_powers)
        self.is_game_active = active
        self.is_game_paused = paused

    def get_dummy_unordered_power_names(self):
        return list(self._dummy_powers)


def _make_server_with_allowlist(allowlist):
    server = object.__new__(Server)
    server.games_with_dummy_powers = {}
    server.dispatched_dummy_powers = {}
    server.bot_dispatch_allowed_root_maps = Server._normalize_root_maps_allowlist(allowlist)
    return server


def test_register_dummy_power_names_default_allowlist_standard_only():
    server = _make_server_with_allowlist(None)

    standard_game = _DummyServerGame('game-standard', 'standard', ['FRANCE'])
    custom_game = _DummyServerGame('game-custom', 'hex3x3', ['AUSTRIA'])

    server.register_dummy_power_names(standard_game)
    server.register_dummy_power_names(custom_game)

    assert server.games_with_dummy_powers == {'game-standard': ['FRANCE']}


def test_register_dummy_power_names_custom_allowlist_includes_hex3x3():
    server = _make_server_with_allowlist(['standard', 'hex3x3'])
    custom_game = _DummyServerGame('game-custom', 'hex3x3', ['AUSTRIA', 'FRANCE'])

    server.register_dummy_power_names(custom_game)

    assert server.games_with_dummy_powers == {'game-custom': ['AUSTRIA', 'FRANCE']}


def test_register_dummy_power_names_clears_previous_registry_if_no_dummy_powers():
    server = _make_server_with_allowlist(['standard', 'hex3x3'])
    game_id = 'game-custom'

    initial = _DummyServerGame(game_id, 'hex3x3', ['FRANCE'])
    empty = _DummyServerGame(game_id, 'hex3x3', [])

    server.register_dummy_power_names(initial)
    assert server.games_with_dummy_powers == {game_id: ['FRANCE']}

    server.register_dummy_power_names(empty)
    assert server.games_with_dummy_powers == {}
    assert server.dispatched_dummy_powers == {}


def test_normalize_root_maps_allowlist_lowercases_and_deduplicates():
    assert Server._normalize_root_maps_allowlist(['Standard', ' HEX3X3 ', 'standard']) == ['standard', 'hex3x3']
