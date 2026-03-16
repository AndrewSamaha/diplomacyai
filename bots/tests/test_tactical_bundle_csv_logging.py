"""Unit tests for tactical bundle CSV logging."""

from pathlib import Path
import csv
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bots.utils.tactical.write_bundle_candidates_csv import write_bundle_candidates_csv


def test_write_bundle_candidates_csv_writes_phase_file(tmp_path):
    logs_root = tmp_path / "logs"
    csv_path = write_bundle_candidates_csv(
        game_name="game_123",
        phase="F1901M",
        power_name="AUSTRIA",
        selected_annotations=["net_score", "risk_score"],
        search_duration_ms=12.345,
        candidate_bundles=[
            {
                "bundle_id": "bundle_1",
                "bundle_rank": 1,
                "bundle_score": 2.5,
                "score_breakdown": {"base_total": 2.0, "total": 2.5},
                "resolution_metadata": {
                    "per_order": [
                        {
                            "intended_order": "A ABC - ACC",
                            "effective_order": "A ABC H",
                            "result": "bounced_duplicate_move_destination",
                        }
                    ],
                    "self_conflict_groups": [{"destination": "ACC"}],
                    "friendly_occupied_conflicts": [],
                    "n_self_bounced_moves": 1,
                    "resolver_iterations": 2,
                },
                "order_annotations": [{"order": "A ABC - ACC", "metrics": {"net_score": 1.2}}],
            }
        ],
        logs_root=str(logs_root),
    )

    expected = logs_root / "game_123" / "F1901M.csv"
    assert Path(csv_path) == expected
    assert expected.exists()

    with expected.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert rows[0]["row_type"] == "bundle_summary"
    assert rows[0]["search_duration_ms"] == "12.345"
    assert rows[1]["row_type"] == "order"
    assert rows[1]["search_duration_ms"] == ""
