"""Write tactical bundle candidates to a flat CSV file."""

import csv
import json
from pathlib import Path


def write_bundle_candidates_csv(
    *,
    game_name: str,
    phase: str,
    power_name: str,
    selected_annotations: list[str],
    candidate_bundles: list[dict[str, object]],
    search_duration_ms: float | None = None,
    logs_root: str = "logs",
) -> str:
    """Append bundle summary and order rows into logs/<game_name>/<phase>.csv."""
    game_dir = Path(logs_root) / str(game_name)
    game_dir.mkdir(parents=True, exist_ok=True)
    csv_path = game_dir / f"{phase}.csv"

    fieldnames = [
        "row_type",
        "game_name",
        "phase",
        "power_name",
        "bundle_rank",
        "bundle_id",
        "bundle_score",
        "search_duration_ms",
        "base_total",
        "capture_bonus",
        "cohesion_bonus",
        "destination_conflict_penalty",
        "leave_center_penalty",
        "exposure_penalty",
        "total",
        "n_self_bounced_moves",
        "resolver_iterations",
        "self_conflict_groups",
        "friendly_occupied_conflicts",
        "selected_annotations",
        "order_index",
        "intended_order",
        "effective_order",
        "order_result",
        "order_annotation_metrics",
    ]

    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()

        for bundle in candidate_bundles:
            breakdown = bundle.get("score_breakdown", {})
            resolution = bundle.get("resolution_metadata", {})
            writer.writerow(
                {
                    "row_type": "bundle_summary",
                    "game_name": game_name,
                    "phase": phase,
                    "power_name": power_name,
                    "bundle_rank": bundle.get("bundle_rank", ""),
                    "bundle_id": bundle.get("bundle_id", ""),
                    "bundle_score": bundle.get("bundle_score", ""),
                    "search_duration_ms": search_duration_ms if search_duration_ms is not None else "",
                    "base_total": breakdown.get("base_total", ""),
                    "capture_bonus": breakdown.get("capture_bonus", ""),
                    "cohesion_bonus": breakdown.get("cohesion_bonus", ""),
                    "destination_conflict_penalty": breakdown.get("destination_conflict_penalty", ""),
                    "leave_center_penalty": breakdown.get("leave_center_penalty", ""),
                    "exposure_penalty": breakdown.get("exposure_penalty", ""),
                    "total": breakdown.get("total", ""),
                    "n_self_bounced_moves": resolution.get("n_self_bounced_moves", ""),
                    "resolver_iterations": resolution.get("resolver_iterations", ""),
                    "self_conflict_groups": json.dumps(
                        resolution.get("self_conflict_groups", []), sort_keys=True
                    ),
                    "friendly_occupied_conflicts": json.dumps(
                        resolution.get("friendly_occupied_conflicts", []), sort_keys=True
                    ),
                    "selected_annotations": json.dumps(selected_annotations, sort_keys=True),
                    "order_index": "",
                    "intended_order": "",
                    "effective_order": "",
                    "order_result": "",
                    "order_annotation_metrics": "",
                }
            )

            per_order = resolution.get("per_order", [])
            annotation_rows = bundle.get("order_annotations", [])
            for idx, order_info in enumerate(per_order):
                annotation_metrics = {}
                if idx < len(annotation_rows):
                    metrics = annotation_rows[idx].get("metrics", {})
                    if isinstance(metrics, dict):
                        annotation_metrics = metrics
                writer.writerow(
                    {
                        "row_type": "order",
                        "game_name": game_name,
                        "phase": phase,
                        "power_name": power_name,
                        "bundle_rank": bundle.get("bundle_rank", ""),
                        "bundle_id": bundle.get("bundle_id", ""),
                        "bundle_score": bundle.get("bundle_score", ""),
                        "search_duration_ms": "",
                        "base_total": "",
                        "capture_bonus": "",
                        "cohesion_bonus": "",
                        "destination_conflict_penalty": "",
                        "leave_center_penalty": "",
                        "exposure_penalty": "",
                        "total": "",
                        "n_self_bounced_moves": "",
                        "resolver_iterations": "",
                        "self_conflict_groups": "",
                        "friendly_occupied_conflicts": "",
                        "selected_annotations": "",
                        "order_index": idx,
                        "intended_order": order_info.get("intended_order", ""),
                        "effective_order": order_info.get("effective_order", ""),
                        "order_result": order_info.get("result", ""),
                        "order_annotation_metrics": json.dumps(annotation_metrics, sort_keys=True),
                    }
                )

    return str(csv_path)
