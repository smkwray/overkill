from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from overkill.discovery import build_overview
from overkill.relationships import DEFAULT_TAXONOMY_PATH, load_bundle_relationships


def build_bundle_audit(
    bundle_root: str | Path,
    *,
    prompt_path: str | Path | None = None,
    taxonomy_path: str | Path = DEFAULT_TAXONOMY_PATH,
) -> dict[str, Any]:
    overview = build_overview(bundle_root, prompt_path=prompt_path)
    taxonomy = load_bundle_relationships(taxonomy_path)

    provisional_bundle_ids = set(taxonomy["provisional_bundle_ids"])
    roles_by_bundle = {row["bundle_id"]: row for row in taxonomy["bundle_roles"]}
    relations_by_bundle: dict[str, list[dict[str, Any]]] = {}
    for relation in taxonomy["relations"]:
        relations_by_bundle.setdefault(relation["bundle_id"], []).append(relation)

    audited_bundles: list[dict[str, Any]] = []
    for bundle in overview["bundles"]:
        bundle_id = bundle["bundle_id"]
        episodes = bundle.get("episodes", []) if bundle["status"] == "valid" else []
        full_episode_count = sum(1 for episode in episodes if episode.get("full_estimate_completed"))
        partial_episode_count = len(episodes) - full_episode_count
        quality_tiers = {
            "A": sum(1 for episode in episodes if episode.get("quality_tier") == "A"),
            "B": sum(1 for episode in episodes if episode.get("quality_tier") == "B"),
            "C": sum(1 for episode in episodes if episode.get("quality_tier") == "C"),
            "D": sum(1 for episode in episodes if episode.get("quality_tier") == "D"),
            "null": sum(1 for episode in episodes if episode.get("quality_tier") is None),
        }

        role_row = roles_by_bundle.get(bundle_id)
        flags: list[str] = []
        if bundle_id in provisional_bundle_ids:
            flags.append("provisional")
        if role_row is not None:
            flags.append(f"role:{role_row['role']}")
        if quality_tiers["D"] > 0:
            flags.append("has_d_quality_episodes")
        if partial_episode_count > full_episode_count:
            flags.append("mostly_partial")

        audited_bundles.append(
            {
                "bundle_id": bundle_id,
                "status": bundle["status"],
                "bundle_role": role_row["role"] if role_row is not None else None,
                "bundle_role_note": role_row["notes"] if role_row is not None else None,
                "flags": flags,
                "full_episode_count": full_episode_count,
                "partial_episode_count": partial_episode_count,
                "quality_tiers": quality_tiers,
                "relations": relations_by_bundle.get(bundle_id, []),
                "conflict_name": bundle.get("conflict_name"),
                "bundle_path": bundle.get("bundle_path"),
            }
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "bundle_root": str(Path(bundle_root)),
        "taxonomy_path": str(Path(taxonomy_path)),
        "bundle_count": overview["bundle_count"],
        "valid_bundle_count": overview["valid_bundle_count"],
        "invalid_bundle_count": overview["invalid_bundle_count"],
        "provisional_bundle_count": len(provisional_bundle_ids),
        "umbrella_bundle_count": sum(
            1 for row in taxonomy["bundle_roles"] if row.get("role") == "umbrella"
        ),
        "repair_prompt_queue": taxonomy["repair_prompt_queue"],
        "deferred_repair_bundle_ids": taxonomy["deferred_repair_bundle_ids"],
        "bundles": audited_bundles,
    }
