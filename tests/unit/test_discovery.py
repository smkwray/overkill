from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from overkill.discovery import (
    _INFLICTING_OVERRIDES,
    _SIDE_COUNTRY_MAP,
    _VICTIM_OVERRIDES,
    PUBLIC_EXPORT_KEYS,
    build_best_supported_episode_export,
    build_overview,
    build_public_overview,
    read_active_target,
    scan_bundle_root,
)


FIXTURE_ROOT = Path("tests/fixtures/bundles")


def test_scan_bundle_root_finds_fixture_bundle() -> None:
    bundles = scan_bundle_root(FIXTURE_ROOT)

    bundle = next(bundle for bundle in bundles if bundle["bundle_id"] == "demo-conflict")
    assert bundle["status"] == "valid"
    assert bundle["conflict_id"] == "demo-conflict"
    assert len(bundle["episodes"]) >= 1
    assert bundle["sources"]
    assert any(source["source_id"] for source in bundle["sources"])

    episode = bundle["episodes"][0]
    assert episode["source_ledger"]
    assert any(source["source_id"] for source in episode["source_ledger"])
    assert episode["episode_types"]
    assert episode["primary_episode_type"] in episode["episode_types"]
    assert isinstance(episode["proxy_limit_flags"], list)


def test_metrics_dict_uses_lists_and_preserves_all_entries() -> None:
    bundles = scan_bundle_root(FIXTURE_ROOT)
    bundle = next(bundle for bundle in bundles if bundle["bundle_id"] == "demo-conflict")
    episode = bundle["episodes"][0]

    for metric_name, entries in episode["metrics"].items():
        assert isinstance(entries, list), f"metrics[{metric_name!r}] should be a list"
        assert len(entries) >= 1

    metric_names_from_rows = [row["metric_name"] for row in episode["metric_rows"]]
    metric_names_from_dict = [
        name for name, entries in episode["metrics"].items() for _ in entries
    ]
    assert sorted(metric_names_from_rows) == sorted(metric_names_from_dict)


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
    assert any(bundle["bundle_id"] == "demo-conflict" for bundle in written["bundles"])


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
                        "bundle_id": "demo-conflict",
                        "role": "umbrella",
                        "notes": "Test umbrella note",
                    }
                ],
                "relations": [
                    {
                        "relation_type": "supersedes_bundle",
                        "bundle_id": "other-bundle",
                        "other_bundle_id": "demo-conflict",
                        "status": "preferred_repair",
                        "notes": "The fixture bundle is superseded in this synthetic test.",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    overview = build_overview(FIXTURE_ROOT, taxonomy_path=taxonomy_path)
    bundle = next(bundle for bundle in overview["bundles"] if bundle["bundle_id"] == "demo-conflict")

    assert bundle["bundle_role"] == "umbrella"
    assert bundle["bundle_role_note"] == "Test umbrella note"
    assert bundle["public_visibility"] == "superseded"
    assert bundle["public_canonical"] is False
    assert bundle["superseded_by"][0]["bundle_id"] == "other-bundle"


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
    fixture_dir = FIXTURE_ROOT / "demo-conflict"
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
    fixture_dir = FIXTURE_ROOT / "demo-conflict"
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


def test_side_country_map_loads_from_json() -> None:
    assert len(_SIDE_COUNTRY_MAP) >= 150
    assert _SIDE_COUNTRY_MAP["palestinians in gaza"] == "Gaza"
    assert _SIDE_COUNTRY_MAP["israeli forces"] == "Israel"


def test_side_overrides_load_with_tuple_keys() -> None:
    assert isinstance(list(_VICTIM_OVERRIDES.keys())[0], tuple)
    assert isinstance(list(_INFLICTING_OVERRIDES.keys())[0], tuple)
    assert len(_VICTIM_OVERRIDES) >= 10
    assert len(_INFLICTING_OVERRIDES) >= 19


def test_public_overview_keeps_results_and_drops_workflow_details(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundles" / "demo-conflict"
    shutil.copytree(FIXTURE_ROOT / "demo-conflict", bundle_dir)
    conflict = json.loads((bundle_dir / "conflict.json").read_text(encoding="utf-8"))
    conflict["notes"] = "Episodes stay inside the city. Rural fronts excluded per prompt. [corrected per definitions.md]"
    (bundle_dir / "conflict.json").write_text(json.dumps(conflict), encoding="utf-8")
    (tmp_path / "bundles" / "broken").mkdir()
    prompt = tmp_path / "gptpro.md"
    prompt.write_text("- In progress: `Demo conflict`\n", encoding="utf-8")

    overview = build_overview(tmp_path / "bundles", prompt_path=prompt)
    public = build_public_overview(overview)
    text = json.dumps(public)

    # The published site shows the estimates, episodes, sources and claims...
    bundle = public["bundles"][0]
    episode = bundle["episodes"][0]
    assert public["bundle_count"] == 1
    full_episode = next(item for item in overview["bundles"] if item["bundle_id"] == "demo-conflict")["episodes"][0]
    assert episode["metric_rows"] == [
        {key: value for key, value in row.items() if key in PUBLIC_EXPORT_KEYS} for row in full_episode["metric_rows"]
    ]
    assert episode["source_ledger"][0]["claims"][0]["excerpt"] == "Demo claim"
    # ...but not local paths, the research prompt's target, notes about the prompt, or invalid bundles.
    assert json.dumps(str(tmp_path))[1:-1] not in text
    assert "active_target" not in public
    assert bundle["notes"] == "Episodes stay inside the city."
    assert [item["bundle_id"] for item in public["bundles"]] == ["demo-conflict"]


def test_public_overview_publishes_only_the_superseding_bundle(tmp_path: Path) -> None:
    # A repair bundle that supersedes an older bundle for the same conflict replaces it on the site,
    # so the conflict is not listed twice with conflicting estimates.
    root = tmp_path / "bundles"
    shutil.copytree(FIXTURE_ROOT / "demo-conflict", root / "demo-conflict")
    shutil.copytree(FIXTURE_ROOT / "demo-conflict", root / "demo-conflict_repair")
    taxonomy_path = tmp_path / "bundle_relationships.json"
    taxonomy_path.write_text(
        json.dumps(
            {
                "relations": [
                    {
                        "relation_type": "supersedes_bundle",
                        "bundle_id": "demo-conflict_repair",
                        "other_bundle_id": "demo-conflict",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    public = build_public_overview(build_overview(root, taxonomy_path=taxonomy_path))

    assert [bundle["bundle_id"] for bundle in public["bundles"]] == ["demo-conflict_repair"]
    assert public["bundle_count"] == public["valid_bundle_count"] == 1


def test_public_overview_rewords_research_process_notes_but_not_estimates(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundles" / "demo-conflict"
    shutil.copytree(FIXTURE_ROOT / "demo-conflict", bundle_dir)
    conflict = json.loads((bundle_dir / "conflict.json").read_text(encoding="utf-8"))
    conflict["notes"] = "This rerun bundle keeps the city footprint. The range is wide in this pass."
    (bundle_dir / "conflict.json").write_text(json.dumps(conflict), encoding="utf-8")

    overview = build_overview(tmp_path / "bundles")
    public = build_public_overview(overview)

    bundle = public["bundles"][0]
    assert bundle["notes"] == "This bundle keeps the city footprint. The range is wide."
    full_rows = overview["bundles"][0]["episodes"][0]["metric_rows"]
    public_rows = bundle["episodes"][0]["metric_rows"]
    for full_row, public_row in zip(full_rows, public_rows, strict=True):
        for key in ("value_low", "value_best", "value_high"):
            assert public_row[key] == full_row[key]


def test_public_export_keeps_every_field_the_explorer_reads() -> None:
    explorer_js = "".join(
        path.read_text(encoding="utf-8") for path in Path("static/demo").rglob("*.js")
    )
    read_by_explorer = set(re.findall(r"\??\.([A-Za-z_]\w*)", explorer_js))
    exported: set[str] = set()

    def collect(value: object) -> None:
        if isinstance(value, dict):
            exported.update(value)
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(build_overview(FIXTURE_ROOT))
    # active_target comes from the private research prompt; "status" matches response.status.
    deliberately_withheld = {"active_target", "status"}
    assert (read_by_explorer & exported) - deliberately_withheld <= PUBLIC_EXPORT_KEYS
