from __future__ import annotations

import json
from pathlib import Path

from overkill.ingest_markdown import expand_markdown_inputs, import_markdown_bundles
from overkill.validation import load_and_validate_bundle


def test_import_markdown_bundle_normalizes_extra_fields_and_validates(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    markdown_path.write_text(
        _build_markdown(
            _bundle_payload(
                conflict_id="demo-conflict",
                conflict_name="Demo conflict",
                include_extra_fields=True,
            ),
            heading_style="required_block",
        ),
        encoding="utf-8",
    )

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    assert len(summary.created) == 1
    created_dir = bundles_root / "demo-conflict"
    assert created_dir.is_dir()

    claims = json.loads((created_dir / "claims.json").read_text(encoding="utf-8"))
    estimates = json.loads((created_dir / "estimates.json").read_text(encoding="utf-8"))
    assert "mortality_measure_type" not in claims[0]
    assert "source_wording_exact" not in estimates[0]

    result = load_and_validate_bundle(created_dir)
    assert result.conflict.conflict_id == "demo-conflict"


def test_import_markdown_bundle_normalizes_blank_episode_quality_tier(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    markdown_path.write_text(
        _build_markdown(
            _bundle_payload(
                conflict_id="demo-conflict",
                conflict_name="Demo conflict",
                episode_quality_tier="",
                episode_full_estimate_completed=False,
            )
        ),
        encoding="utf-8",
    )

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    created_dir = bundles_root / "demo-conflict"
    episodes = json.loads((created_dir / "episodes.json").read_text(encoding="utf-8"))
    assert episodes[0]["quality_tier"] is None

    result = load_and_validate_bundle(created_dir)
    assert result.conflict.conflict_id == "demo-conflict"


def test_import_markdown_bundle_normalizes_blank_conflict_end_date(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    payload = _bundle_payload(conflict_id="demo-conflict", conflict_name="Demo conflict")
    payload["conflict.json"]["end_date"] = ""
    markdown_path.write_text(_build_markdown(payload), encoding="utf-8")

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    conflict = json.loads((bundles_root / "demo-conflict" / "conflict.json").read_text(encoding="utf-8"))
    assert conflict["end_date"] is None

    result = load_and_validate_bundle(bundles_root / "demo-conflict")
    assert result.conflict.end_date is None


def test_import_markdown_bundle_accepts_open_ended_episode(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    markdown_path.write_text(
        _build_markdown(
            _bundle_payload(
                conflict_id="demo-conflict",
                conflict_name="Demo conflict",
                episode_quality_tier=None,
                episode_full_estimate_completed=False,
                episode_end_date=None,
            )
        ),
        encoding="utf-8",
    )

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    created_dir = bundles_root / "demo-conflict"
    episodes = json.loads((created_dir / "episodes.json").read_text(encoding="utf-8"))
    assert episodes[0]["end_date"] is None

    result = load_and_validate_bundle(created_dir)
    assert result.episodes[0].end_date is None


def test_import_markdown_bundle_normalizes_assumption_category_aliases(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    payload = _bundle_payload(conflict_id="demo-conflict", conflict_name="Demo conflict")
    payload["assumptions.json"][0]["category"] = "population"
    markdown_path.write_text(_build_markdown(payload), encoding="utf-8")

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    assumptions = json.loads((bundles_root / "demo-conflict" / "assumptions.json").read_text(encoding="utf-8"))
    assert assumptions[0]["category"] == "displacement"

    result = load_and_validate_bundle(bundles_root / "demo-conflict")
    assert result.assumptions[0].category == "displacement"


def test_import_markdown_bundle_normalizes_status_mix_assumption_alias(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    payload = _bundle_payload(conflict_id="demo-conflict", conflict_name="Demo conflict")
    payload["assumptions.json"][0]["category"] = "status_mix"
    markdown_path.write_text(_build_markdown(payload), encoding="utf-8")

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    assumptions = json.loads((bundles_root / "demo-conflict" / "assumptions.json").read_text(encoding="utf-8"))
    assert assumptions[0]["category"] == "casualty_status"

    result = load_and_validate_bundle(bundles_root / "demo-conflict")
    assert result.assumptions[0].category == "casualty_status"


def test_import_markdown_bundle_normalizes_prose_enums_and_dr_unknown_status_rule(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    payload = _bundle_payload(conflict_id="demo-conflict", conflict_name="Demo conflict")
    payload["claims.json"][0]["population_class"] = "total"
    payload["claims.json"][0]["estimate_method"] = "Official commission supported upper/best figure"
    payload["estimates.json"][0]["estimate_method"] = "Envelope from mixed-source summary"
    dr_estimate = next(estimate for estimate in payload["estimates.json"] if estimate["metric_name"] == "dr_v1_direct")
    dr_estimate["unknown_status_rule"] = "not_applicable"
    markdown_path.write_text(_build_markdown(payload), encoding="utf-8")

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    claims = json.loads((bundles_root / "demo-conflict" / "claims.json").read_text(encoding="utf-8"))
    estimates = json.loads((bundles_root / "demo-conflict" / "estimates.json").read_text(encoding="utf-8"))
    assert claims[0]["population_class"] == "unknown"
    assert claims[0]["estimate_method"] == "source_direct"
    assert estimates[0]["estimate_method"] == "derived_from_sources"
    assert next(row for row in estimates if row["metric_name"] == "dr_v1_direct")["unknown_status_rule"] == "strict"

    result = load_and_validate_bundle(bundles_root / "demo-conflict")
    assert result.conflict.conflict_id == "demo-conflict"


def test_import_markdown_bundle_normalizes_assumption_scope_and_sensitivity_text(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    payload = _bundle_payload(conflict_id="demo-conflict", conflict_name="Demo conflict")
    payload["assumptions.json"][0]["category"] = "scope"
    payload["assumptions.json"][0]["sensitivity"] = "Low-to-medium."
    markdown_path.write_text(_build_markdown(payload), encoding="utf-8")

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    assumptions = json.loads((bundles_root / "demo-conflict" / "assumptions.json").read_text(encoding="utf-8"))
    assert assumptions[0]["category"] == "geometry"
    assert assumptions[0]["sensitivity"] == "medium"

    result = load_and_validate_bundle(bundles_root / "demo-conflict")
    assert result.assumptions[0].category == "geometry"
    assert result.assumptions[0].sensitivity == "medium"


def test_import_markdown_bundle_falls_back_unknown_assumption_category_to_other(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    payload = _bundle_payload(conflict_id="demo-conflict", conflict_name="Demo conflict")
    payload["assumptions.json"][0]["category"] = "evidence_quality"
    payload["assumptions.json"][0]["sensitivity"] = "High; narrative note."
    markdown_path.write_text(_build_markdown(payload), encoding="utf-8")

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    assumptions = json.loads((bundles_root / "demo-conflict" / "assumptions.json").read_text(encoding="utf-8"))
    assert assumptions[0]["category"] == "other"
    assert assumptions[0]["sensitivity"] == "high"


def test_import_markdown_bundle_drops_null_dr_placeholders(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    payload = _bundle_payload(conflict_id="demo-conflict", conflict_name="Demo conflict")
    payload["episodes.json"][0]["full_estimate_completed"] = False
    dr_estimate = next(estimate for estimate in payload["estimates.json"] if estimate["metric_name"] == "dr_v1_direct")
    dr_estimate["value_low"] = None
    dr_estimate["value_best"] = None
    dr_estimate["value_high"] = None
    dr_estimate["formula_note"] = "DR withheld."
    dr_estimate["uncertainty_note"] = "Missing component estimates."
    markdown_path.write_text(_build_markdown(payload), encoding="utf-8")

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    estimates = json.loads((bundles_root / "demo-conflict" / "estimates.json").read_text(encoding="utf-8"))
    assert [row["metric_name"] for row in estimates] == [
        "mil_deaths_direct",
        "civ_deaths_direct",
        "mil_person_months",
        "civ_person_months",
    ]

    result = load_and_validate_bundle(bundles_root / "demo-conflict")
    assert len(result.estimates) == 4


def test_import_markdown_bundle_drops_dr_metrics_for_incomplete_episode(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    payload = _bundle_payload(
        conflict_id="demo-conflict",
        conflict_name="Demo conflict",
        episode_full_estimate_completed=False,
    )
    payload["estimates.json"].append(
        {
            "estimate_id": "EST-6",
            "episode_id": "EP-1",
            "metric_name": "dr_midpoint_fallback",
            "value_low": 0.5,
            "value_best": 1.0,
            "value_high": 1.5,
            "unit": "deaths per person-month",
            "estimate_method": "derived_from_sources",
            "input_claim_ids": ["CLM-2", "CLM-4"],
            "formula_note": "fallback only",
            "uncertainty_note": "test",
            "unknown_status_rule": "strict",
            "quality_tier": "D",
            "quality_note": "test",
        }
    )
    markdown_path.write_text(_build_markdown(payload), encoding="utf-8")

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    estimates = json.loads((bundles_root / "demo-conflict" / "estimates.json").read_text(encoding="utf-8"))
    assert [row["metric_name"] for row in estimates] == [
        "mil_deaths_direct",
        "civ_deaths_direct",
        "mil_person_months",
        "civ_person_months",
    ]

    result = load_and_validate_bundle(bundles_root / "demo-conflict")
    assert len(result.estimates) == 4


def test_import_markdown_bundle_drops_null_placeholder_estimate_with_empty_claim_refs(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    payload = _bundle_payload(conflict_id="demo-conflict", conflict_name="Demo conflict")
    payload["episodes.json"][0]["full_estimate_completed"] = False
    payload["estimates.json"].append(
        {
            "estimate_id": "EST-6",
            "episode_id": "EP-1",
            "metric_name": "mil_deaths_direct",
            "value_low": None,
            "value_best": None,
            "value_high": None,
            "unit": "deaths",
            "estimate_method": "derived_from_sources",
            "input_claim_ids": [],
            "formula_note": "No evidence recovered.",
            "uncertainty_note": "Placeholder only.",
            "unknown_status_rule": "strict",
            "quality_tier": "D",
            "quality_note": "Not publishable.",
        }
    )
    markdown_path.write_text(_build_markdown(payload), encoding="utf-8")

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    estimates = json.loads((bundles_root / "demo-conflict" / "estimates.json").read_text(encoding="utf-8"))
    assert all(row["estimate_id"] != "EST-6" for row in estimates)

    result = load_and_validate_bundle(bundles_root / "demo-conflict")
    assert all(estimate.estimate_id != "EST-6" for estimate in result.estimates)


def test_import_markdown_bundle_demotes_completed_episode_when_only_null_dr_placeholder_exists(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    payload = _bundle_payload(conflict_id="demo-conflict", conflict_name="Demo conflict")
    dr_estimate = next(estimate for estimate in payload["estimates.json"] if estimate["metric_name"] == "dr_v1_direct")
    dr_estimate["value_low"] = None
    dr_estimate["value_best"] = None
    dr_estimate["value_high"] = None
    markdown_path.write_text(_build_markdown(payload), encoding="utf-8")

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    episodes = json.loads((bundles_root / "demo-conflict" / "episodes.json").read_text(encoding="utf-8"))
    estimates = json.loads((bundles_root / "demo-conflict" / "estimates.json").read_text(encoding="utf-8"))
    assert episodes[0]["full_estimate_completed"] is False
    assert [row["metric_name"] for row in estimates] == [
        "mil_deaths_direct",
        "civ_deaths_direct",
        "mil_person_months",
        "civ_person_months",
    ]

    result = load_and_validate_bundle(bundles_root / "demo-conflict")
    assert result.episodes[0].full_estimate_completed is False


def test_import_markdown_bundle_normalizes_quality_tier_aliases(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    payload = _bundle_payload(conflict_id="demo-conflict", conflict_name="Demo conflict")
    payload["episodes.json"][0]["quality_tier"] = "medium"
    payload["estimates.json"][0]["quality_tier"] = "B-"
    payload["estimates.json"][1]["quality_tier"] = "C+"
    markdown_path.write_text(_build_markdown(payload), encoding="utf-8")

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    episodes = json.loads((bundles_root / "demo-conflict" / "episodes.json").read_text(encoding="utf-8"))
    estimates = json.loads((bundles_root / "demo-conflict" / "estimates.json").read_text(encoding="utf-8"))
    assert episodes[0]["quality_tier"] == "C"
    assert estimates[0]["quality_tier"] == "B"
    assert estimates[1]["quality_tier"] == "C"


def test_import_markdown_bundle_normalizes_underscored_quality_tier_aliases(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    payload = _bundle_payload(conflict_id="demo-conflict", conflict_name="Demo conflict")
    payload["episodes.json"][0]["quality_tier"] = "low_medium"
    payload["estimates.json"][0]["quality_tier"] = "medium_high"
    markdown_path.write_text(_build_markdown(payload), encoding="utf-8")

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    episodes = json.loads((bundles_root / "demo-conflict" / "episodes.json").read_text(encoding="utf-8"))
    estimates = json.loads((bundles_root / "demo-conflict" / "estimates.json").read_text(encoding="utf-8"))
    assert episodes[0]["quality_tier"] == "C"
    assert estimates[0]["quality_tier"] == "B"


def test_import_markdown_bundle_skips_existing_without_overwrite(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    markdown_path.write_text(
        _build_markdown(_bundle_payload(conflict_id="demo-conflict", conflict_name="Demo conflict")),
        encoding="utf-8",
    )
    bundles_root = tmp_path / "bundles"

    first = import_markdown_bundles([markdown_path], bundles_root=bundles_root)
    second = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert len(first.created) == 1
    assert len(second.created) == 0
    assert len(second.skipped_existing) == 1
    assert second.skipped_existing[0].conflict_id == "demo-conflict"


def test_import_markdown_bundle_prefers_non_copy_filename(tmp_path: Path) -> None:
    primary = tmp_path / "overkill_demo-conflict_research_bundle.md"
    duplicate_copy = tmp_path / "overkill_demo-conflict_research_bundle (1).md"

    primary.write_text(
        _build_markdown(_bundle_payload(conflict_id="demo-conflict", conflict_name="Primary Source")),
        encoding="utf-8",
    )
    duplicate_copy.write_text(
        _build_markdown(_bundle_payload(conflict_id="demo-conflict", conflict_name="Copy Source")),
        encoding="utf-8",
    )

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([duplicate_copy, primary], bundles_root=bundles_root)

    assert summary.error_count == 0
    assert len(summary.created) == 1
    assert len(summary.skipped_duplicate_inputs) == 1

    conflict = json.loads((bundles_root / "demo-conflict" / "conflict.json").read_text(encoding="utf-8"))
    assert conflict["conflict_name"] == "Primary Source"


def test_expand_markdown_inputs_handles_directory_and_file_mix(tmp_path: Path) -> None:
    folder = tmp_path / "downloads"
    folder.mkdir()
    first = folder / "overkill_first_research_bundle.md"
    second = folder / "overkill_second_research_bundle.md"
    ignored = folder / "notes.md"
    first.write_text("x", encoding="utf-8")
    second.write_text("y", encoding="utf-8")
    ignored.write_text("z", encoding="utf-8")

    expanded = expand_markdown_inputs([folder, first])

    names = [path.name for path in expanded]
    assert names == ["overkill_first_research_bundle.md", "overkill_second_research_bundle.md"]


def test_import_markdown_bundle_accepts_filename_labeled_fences(tmp_path: Path) -> None:
    markdown_path = tmp_path / "overkill_demo-conflict_research_bundle.md"
    markdown_path.write_text(_build_markdown(_bundle_payload(conflict_id="demo-conflict", conflict_name="Demo conflict"), fence_label="conflict.json"), encoding="utf-8")

    bundles_root = tmp_path / "bundles"
    summary = import_markdown_bundles([markdown_path], bundles_root=bundles_root)

    assert summary.error_count == 0
    result = load_and_validate_bundle(bundles_root / "demo-conflict")
    assert result.conflict.conflict_id == "demo-conflict"


def _build_markdown(
    payloads: dict[str, object],
    *,
    heading_style: str = "plain",
    fence_label: str = "json",
) -> str:
    lines = ["# Demo bundle", "", "## 9. Machine-readable bundle", ""]
    for index, filename in enumerate(
        [
            "conflict.json",
            "episodes.json",
            "sources.json",
            "claims.json",
            "estimates.json",
            "assumptions.json",
            "open_questions.json",
        ],
        start=1,
    ):
        if heading_style == "required_block":
            lines.append(f"## Required JSON block {index} - `{filename}`")
        else:
            lines.append(f"### {filename}")
        lines.append(f"```{fence_label}")
        lines.append(json.dumps(payloads[filename], indent=2))
        lines.append("```")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _bundle_payload(
    *,
    conflict_id: str,
    conflict_name: str,
    include_extra_fields: bool = False,
    episode_quality_tier: str | None = "C",
    episode_full_estimate_completed: bool = True,
    episode_end_date: str | None = "2020-01-31",
) -> dict[str, object]:
    claim = {
        "claim_id": "CLM-1",
        "episode_id": "EP-1",
        "source_id": "SRC-1",
        "variable_name": "mil_deaths_direct",
        "population_class": "military",
        "death_type": "direct",
        "start_date": "2020-01-01",
        "end_date": "2020-01-31",
        "geographic_scope": "Test city",
        "value_low": 10,
        "value_best": 12,
        "value_high": 15,
        "unit": "deaths",
        "estimate_method": "source_direct",
        "excerpt": "Example military deaths claim",
        "pages_or_sections": "p. 1",
        "transform_note": "",
        "confidence_note": "medium",
    }
    claim_civ = {
        **claim,
        "claim_id": "CLM-2",
        "variable_name": "civ_deaths_direct",
        "population_class": "civilian",
        "value_low": 5,
        "value_best": 6,
        "value_high": 7,
        "excerpt": "Example civilian deaths claim",
    }
    claim_mil_pm = {
        **claim,
        "claim_id": "CLM-3",
        "variable_name": "mil_person_months",
        "death_type": "not_applicable",
        "value_low": 100,
        "value_best": 120,
        "value_high": 140,
        "unit": "person_months",
        "excerpt": "Example military person-months claim",
    }
    claim_civ_pm = {
        **claim_civ,
        "claim_id": "CLM-4",
        "variable_name": "civ_person_months",
        "death_type": "not_applicable",
        "value_low": 1000,
        "value_best": 1200,
        "value_high": 1400,
        "unit": "person_months",
        "excerpt": "Example civilian person-months claim",
    }
    if include_extra_fields:
        claim["mortality_measure_type"] = "direct_deaths"
        claim_civ["source_wording_exact"] = "example quote"

    estimate_mil = {
        "estimate_id": "EST-1",
        "episode_id": "EP-1",
        "metric_name": "mil_deaths_direct",
        "value_low": 10,
        "value_best": 12,
        "value_high": 15,
        "unit": "deaths",
        "estimate_method": "derived_from_sources",
        "input_claim_ids": ["CLM-1"],
        "formula_note": "source interval",
        "uncertainty_note": "test",
        "unknown_status_rule": "strict",
        "quality_tier": "C",
        "quality_note": "test",
    }
    estimate_civ = {
        **estimate_mil,
        "estimate_id": "EST-2",
        "metric_name": "civ_deaths_direct",
        "value_low": 5,
        "value_best": 6,
        "value_high": 7,
        "input_claim_ids": ["CLM-2"],
    }
    estimate_mil_pm = {
        **estimate_mil,
        "estimate_id": "EST-3",
        "metric_name": "mil_person_months",
        "value_low": 100,
        "value_best": 120,
        "value_high": 140,
        "unit": "person_months",
        "input_claim_ids": ["CLM-3"],
        "unknown_status_rule": "not_applicable",
    }
    estimate_civ_pm = {
        **estimate_mil_pm,
        "estimate_id": "EST-4",
        "metric_name": "civ_person_months",
        "value_low": 1000,
        "value_best": 1200,
        "value_high": 1400,
        "input_claim_ids": ["CLM-4"],
    }
    estimate_dr = {
        **estimate_mil,
        "estimate_id": "EST-5",
        "metric_name": "dr_v1_direct",
        "value_low": 10.204081632653061,
        "value_best": 20.0,
        "value_high": 42.0,
        "unit": "ratio",
        "input_claim_ids": ["CLM-1", "CLM-2", "CLM-3", "CLM-4"],
    }
    if include_extra_fields:
        estimate_mil["source_wording_exact"] = "extra estimate note"
        estimate_civ["mortality_measure_type"] = "direct_deaths"

    estimates = [estimate_mil, estimate_civ, estimate_mil_pm, estimate_civ_pm]
    if episode_full_estimate_completed:
        estimates.append(estimate_dr)

    return {
        "conflict.json": {
            "conflict_id": conflict_id,
            "conflict_name": conflict_name,
            "aliases": [],
            "family_summary": "demo summary",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "countries": ["Exampleland"],
            "regions": ["Example region"],
            "notes": "",
            "slug": "demo-conflict",
        },
        "episodes.json": [
            {
                "episode_id": "EP-1",
                "conflict_id": conflict_id,
                "episode_name": "Demo episode",
                "start_date": "2020-01-01",
                "end_date": episode_end_date,
                "time_unit": "month",
                "geographic_scope": "city",
                "countries": ["Exampleland"],
                "admin_units": ["Demo admin unit"],
                "theater_description": "demo theater",
                "geometry_method_note": "demo",
                "military_area_note": "demo",
                "civilian_area_note": "demo",
                "split_reason": "demo",
                "full_estimate_completed": episode_full_estimate_completed,
                "quality_tier": episode_quality_tier,
                "quality_note": "demo",
            }
        ],
        "sources.json": [
            {
                "source_id": "SRC-1",
                "citation_short": "Demo source",
                "title": "Demo title",
                "author_or_org": "Demo org",
                "year": "2020",
                "source_type": "report",
                "url": "https://example.com/source",
                "pages_or_sections": "p. 1",
                "geographic_scope": "Test city",
                "date_scope": "2020-01",
                "variables_supported": ["mil_deaths_direct", "civ_deaths_direct"],
                "strengths": "demo",
                "limitations": "demo",
                "notes": "",
            }
        ],
        "claims.json": [claim, claim_civ, claim_mil_pm, claim_civ_pm],
        "estimates.json": estimates,
        "assumptions.json": [
            {
                "assumption_id": "ASM-1",
                "episode_id": "EP-1",
                "category": "other",
                "assumption_text": "demo",
                "rationale": "demo",
                "sensitivity": "medium",
            }
        ],
        "open_questions.json": [
            {
                "episode_id": "EP-1",
                "question": "demo",
                "why_it_matters": "demo",
                "what_would_resolve_it": "demo",
            }
        ],
    }
