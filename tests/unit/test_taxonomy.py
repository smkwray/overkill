from __future__ import annotations

import json
from pathlib import Path

from overkill.taxonomy import build_bundle_audit, load_bundle_relationships


def test_load_bundle_relationships_defaults_when_missing(tmp_path: Path) -> None:
    payload = load_bundle_relationships(tmp_path / "missing.json")

    assert payload["version"] == 1
    assert payload["provisional_bundle_ids"] == []
    assert payload["bundle_roles"] == []
    assert payload["relations"] == []
    assert payload["repair_prompt_queue"] == []


def test_build_bundle_audit_applies_relationship_metadata(tmp_path: Path) -> None:
    taxonomy_path = tmp_path / "bundle_relationships.json"
    taxonomy_path.write_text(
        json.dumps(
            {
                "version": 1,
                "updated_at": "2026-03-09T14:03:00-04:00",
                "provisional_bundle_ids": ["bosnian-war"],
                "bundle_roles": [
                    {
                        "bundle_id": "bosnian-war",
                        "role": "umbrella",
                        "notes": "Test role note",
                    }
                ],
                "relations": [
                    {
                        "relation_type": "supersedes_episode",
                        "bundle_id": "bosnian-war",
                        "other_bundle_id": "other-bundle",
                        "other_episode_name": "Episode A",
                        "status": "planned_canonical",
                        "notes": "Test relation note",
                    }
                ],
                "repair_prompt_queue": [
                    {
                        "prompt_path": "conflicts/example-repair.md",
                        "target_bundle_id": "bosnian-war",
                        "priority": 1,
                    }
                ],
                "deferred_repair_bundle_ids": ["example-bundle"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    audit = build_bundle_audit(
        Path("research/input/gptpro"),
        taxonomy_path=taxonomy_path,
    )

    assert audit["bundle_count"] >= 1
    assert audit["provisional_bundle_count"] == 1
    assert audit["umbrella_bundle_count"] == 1
    assert audit["repair_prompt_queue"][0]["target_bundle_id"] == "bosnian-war"
    assert audit["deferred_repair_bundle_ids"] == ["example-bundle"]

    bosnia = next(bundle for bundle in audit["bundles"] if bundle["bundle_id"] == "bosnian-war")
    assert "provisional" in bosnia["flags"]
    assert "role:umbrella" in bosnia["flags"]
    assert bosnia["bundle_role"] == "umbrella"
    assert bosnia["bundle_role_note"] == "Test role note"
    assert bosnia["relations"][0]["other_bundle_id"] == "other-bundle"
    assert bosnia["full_episode_count"] + bosnia["partial_episode_count"] >= 1
