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
                "provisional_bundle_ids": ["demo-conflict"],
                "bundle_roles": [
                    {
                        "bundle_id": "demo-conflict",
                        "role": "umbrella",
                        "notes": "Test role note",
                    }
                ],
                "relations": [
                    {
                        "relation_type": "supersedes_episode",
                        "bundle_id": "demo-conflict",
                        "other_bundle_id": "other-bundle",
                        "other_episode_name": "Episode A",
                        "status": "planned_canonical",
                        "notes": "Test relation note",
                    }
                ],
                "repair_prompt_queue": [
                    {
                        "prompt_path": "conflicts/example-repair.md",
                        "target_bundle_id": "demo-conflict",
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
        Path("tests/fixtures/bundles"),
        taxonomy_path=taxonomy_path,
    )

    assert audit["bundle_count"] >= 1
    assert audit["provisional_bundle_count"] == 1
    assert audit["umbrella_bundle_count"] == 1
    assert audit["repair_prompt_queue"][0]["target_bundle_id"] == "demo-conflict"
    assert audit["deferred_repair_bundle_ids"] == ["example-bundle"]

    bundle = next(bundle for bundle in audit["bundles"] if bundle["bundle_id"] == "demo-conflict")
    assert "provisional" in bundle["flags"]
    assert "role:umbrella" in bundle["flags"]
    assert bundle["bundle_role"] == "umbrella"
    assert bundle["bundle_role_note"] == "Test role note"
    assert bundle["relations"][0]["other_bundle_id"] == "other-bundle"
    assert bundle["full_episode_count"] + bundle["partial_episode_count"] >= 1


def test_build_bundle_audit_forwards_taxonomy_path(tmp_path: Path, monkeypatch) -> None:
    captured: dict = {}
    original_build_overview = __import__("overkill.discovery", fromlist=["build_overview"]).build_overview

    def patched_build_overview(*args, **kwargs):
        captured["taxonomy_path"] = kwargs.get("taxonomy_path")
        return original_build_overview(*args, **kwargs)

    monkeypatch.setattr("overkill.taxonomy.build_overview", patched_build_overview)

    custom_taxonomy = tmp_path / "custom_taxonomy.json"
    custom_taxonomy.write_text(
        json.dumps(
            {
                "version": 1,
                "updated_at": "2026-03-09T14:03:00-04:00",
                "provisional_bundle_ids": [],
                "bundle_roles": [],
                "relations": [],
                "repair_prompt_queue": [],
                "deferred_repair_bundle_ids": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    build_bundle_audit(
        Path("tests/fixtures/bundles"),
        taxonomy_path=custom_taxonomy,
    )

    assert captured["taxonomy_path"] == custom_taxonomy
