from __future__ import annotations

import json
from pathlib import Path

from overkill.discovery import build_best_supported_episode_export, build_overview, read_active_target, scan_bundle_root


FIXTURE_ROOT = Path("research/input/gptpro")


def test_scan_bundle_root_finds_bosnia_bundle() -> None:
    bundles = scan_bundle_root(FIXTURE_ROOT)

    bosnia = next(bundle for bundle in bundles if bundle["bundle_id"] == "bosnian-war")
    assert bosnia["status"] == "valid"
    assert bosnia["conflict_id"] == "bosnian-war"
    assert len(bosnia["episodes"]) >= 1
    assert bosnia["sources"]
    assert any(source["source_id"] for source in bosnia["sources"])

    episode = bosnia["episodes"][0]
    assert episode["source_ledger"]
    assert any(source["source_id"] for source in episode["source_ledger"])
    assert episode["episode_types"]
    assert episode["primary_episode_type"] in episode["episode_types"]
    assert isinstance(episode["proxy_limit_flags"], list)


def test_read_active_target_parses_prompt(tmp_path: Path) -> None:
    prompt = tmp_path / "gptpro.md"
    prompt.write_text(
        "\n".join(
            [
                "## Current research target",
                "",
                "- In progress: `Iraq War / occupation`",
                "- Focus/theater/phase: `Start with episodeization`",
                "- Date range: `2003-03-20` to `2011-12-18`",
                "- Working note: `Do not use whole-country denominators for local battles.`",
            ]
        ),
        encoding="utf-8",
    )

    target = read_active_target(prompt)

    assert target == {
        "conflict_name": "Iraq War / occupation",
        "focus": "Start with episodeization",
        "date_range": "2003-03-20 to 2011-12-18",
        "note": "Do not use whole-country denominators for local battles.",
    }


def test_build_overview_and_export_shape(tmp_path: Path) -> None:
    overview = build_overview(FIXTURE_ROOT, prompt_path=Path("gptpro.md"))

    output = tmp_path / "bundles.json"
    output.write_text(json.dumps(overview, indent=2), encoding="utf-8")
    written = json.loads(output.read_text(encoding="utf-8"))

    assert written["bundle_count"] >= 1
    assert written["valid_bundle_count"] >= 1
    assert "taxonomy" in written
    assert "best_supported_episodes" in written
    assert "side_attribution_summary" in written
    assert any(bundle["bundle_id"] == "bosnian-war" for bundle in written["bundles"])


def test_build_overview_applies_taxonomy_metadata(tmp_path: Path) -> None:
    taxonomy_path = tmp_path / "bundle_relationships.json"
    taxonomy_path.write_text(
        json.dumps(
            {
                "version": 1,
                "updated_at": "2026-03-10T09:00:00-04:00",
                "provisional_bundle_ids": [],
                "bundle_roles": [
                    {
                        "bundle_id": "bosnian-war",
                        "role": "umbrella",
                        "notes": "Test umbrella note",
                    }
                ],
                "relations": [
                    {
                        "relation_type": "supersedes_bundle",
                        "bundle_id": "other-bundle",
                        "other_bundle_id": "bosnian-war",
                        "status": "preferred_repair",
                        "notes": "Bosnia is superseded in this synthetic test.",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    overview = build_overview(FIXTURE_ROOT, taxonomy_path=taxonomy_path)
    bosnia = next(bundle for bundle in overview["bundles"] if bundle["bundle_id"] == "bosnian-war")

    assert bosnia["bundle_role"] == "umbrella"
    assert bosnia["bundle_role_note"] == "Test umbrella note"
    assert bosnia["public_visibility"] == "superseded"
    assert bosnia["public_canonical"] is False
    assert bosnia["superseded_by"][0]["bundle_id"] == "other-bundle"


def test_best_supported_episode_export_includes_publishable_episode() -> None:
    export = build_best_supported_episode_export(FIXTURE_ROOT)

    assert export["episode_count"] >= 1
    episode = export["episodes"][0]
    assert episode["bundle_id"]
    assert episode["readiness"] == "publishable_dr"
    assert episode["dr_v1_direct"] is not None


def test_discovery_serializes_optional_side_attribution_fields(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    fixture_dir = Path("research/input/gptpro/bosnian-war")
    for path in fixture_dir.iterdir():
        if path.is_file():
            (bundle_dir / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    claims = json.loads((bundle_dir / "claims.json").read_text(encoding="utf-8"))
    claims[0]["victim_side"] = "Bosnian government-held Sarajevo"
    claims[0]["inflicting_side"] = "Bosnian Serb forces"
    (bundle_dir / "claims.json").write_text(json.dumps(claims, indent=2) + "\n", encoding="utf-8")

    estimates = json.loads((bundle_dir / "estimates.json").read_text(encoding="utf-8"))
    estimates[0]["victim_side"] = "Bosnian government-held Sarajevo"
    estimates[0]["inflicting_side"] = "Bosnian Serb forces"
    (bundle_dir / "estimates.json").write_text(json.dumps(estimates, indent=2) + "\n", encoding="utf-8")

    overview = build_overview(tmp_path)
    bundle = next(item for item in overview["bundles"] if item["bundle_id"] == "bundle")
    episode = bundle["episodes"][0]

    assert episode["source_ledger"][0]["claims"][0]["victim_side"] is not None
    assert episode["source_ledger"][0]["claims"][0]["inflicting_side"] is not None
    assert any(
        row["victim_side"] == "Bosnian government-held Sarajevo"
        and row["inflicting_side"] == "Bosnian Serb forces"
        for row in episode["metric_rows"]
    )


def test_discovery_serializes_open_ended_episode_dates(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    fixture_dir = Path("research/input/gptpro/bosnian-war")
    for path in fixture_dir.iterdir():
        if path.is_file():
            (bundle_dir / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    episodes = json.loads((bundle_dir / "episodes.json").read_text(encoding="utf-8"))
    episodes[0]["full_estimate_completed"] = False
    episodes[0]["quality_tier"] = None
    episodes[0]["end_date"] = None
    (bundle_dir / "episodes.json").write_text(json.dumps(episodes, indent=2) + "\n", encoding="utf-8")

    estimates = json.loads((bundle_dir / "estimates.json").read_text(encoding="utf-8"))
    estimates = [
        estimate
        for estimate in estimates
        if estimate["metric_name"] != "dr_v1_direct"
    ]
    (bundle_dir / "estimates.json").write_text(json.dumps(estimates, indent=2) + "\n", encoding="utf-8")

    overview = build_overview(tmp_path)
    bundle = next(item for item in overview["bundles"] if item["bundle_id"] == "bundle")
    assert bundle["episodes"][0]["end_date"] is None


def test_read_active_target_falls_back_to_do_prompt(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    prompt_dir = workspace / "do"
    prompt_dir.mkdir()
    (prompt_dir / "gptpro.md").write_text(
        "\n".join(
            [
                "## Current research target",
                "",
                "- In progress: `Iraq War / occupation`",
                "- Focus/theater/phase: `Episodeization`",
                "- Date range: `2003-03-20` to `2011-12-18`",
                "- Working note: `Keep local denominators local.`",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(workspace)

    target = read_active_target(Path("gptpro.md"))

    assert target == {
        "conflict_name": "Iraq War / occupation",
        "focus": "Episodeization",
        "date_range": "2003-03-20 to 2011-12-18",
        "note": "Keep local denominators local.",
    }
