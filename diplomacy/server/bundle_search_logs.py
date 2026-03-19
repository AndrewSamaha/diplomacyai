"""Helpers for loading bundle search log CSVs for a game."""

import csv
import logging
import os
from pathlib import Path


LOGGER = logging.getLogger(__name__)
ENABLE_BUNDLE_SEARCH_LOGS_ENV = 'DIPLOMACY_ENABLE_BUNDLE_SEARCH_LOGS'
BUNDLE_SEARCH_LOGS_ROOT_ENV = 'DIPLOMACY_BUNDLE_SEARCH_LOGS_ROOT'
TRUE_VALUES = {'1', 'true', 'yes', 'on'}


def bundle_search_logs_enabled():
    """Return True when bundle search log loading is enabled."""
    return os.getenv(ENABLE_BUNDLE_SEARCH_LOGS_ENV, '').strip().lower() in TRUE_VALUES


def get_bundle_search_logs_root():
    """Return the root directory that contains per-game bundle search CSVs."""
    return Path(os.getenv(BUNDLE_SEARCH_LOGS_ROOT_ENV, 'logs'))


def load_bundle_search_logs_for_game(game_id):
    """Load bundle search CSVs for a game and return {phase_name: [row_dict, ...]}."""
    if not bundle_search_logs_enabled() or not game_id:
        return {}

    game_dir = get_bundle_search_logs_root() / str(game_id)
    if not game_dir.exists() or not game_dir.is_dir():
        return {}

    bundle_search_logs = {}
    for csv_path in sorted(game_dir.glob('*.csv')):
        try:
            with csv_path.open('r', newline='', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                bundle_search_logs[csv_path.stem] = [
                    {key: '' if value is None else value for key, value in row.items()}
                    for row in reader
                ]
        except OSError as exc:
            LOGGER.warning('Unable to read bundle search CSV %s: %s', csv_path, exc)
        except csv.Error as exc:
            LOGGER.warning('Unable to parse bundle search CSV %s: %s', csv_path, exc)
    return bundle_search_logs
