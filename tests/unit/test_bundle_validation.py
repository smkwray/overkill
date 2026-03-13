from __future__ import annotations

import json
from pathlib import Path

import pytest

from overkill.validation import BundleValidationError, load_and_validate_bundle


FIXTURE_DIR = Path("research/input/gptpro/bosnian-war")
IRAQ_FIXTURE_DIR = Path("research/input/gptpro/irq-war-occupation-2003-2011")
SYRIA_FIXTURE_DIR = Path("research/input/gptpro/syria-civil-war-2011-present")


def test_bosnia_bundle_validates() -> None:
    result = load_and_validate_bundle(FIXTURE_DIR)

    assert result.conflict.conflict_id == "bosnian-war"
    assert len(result.episodes) == 4
    assert len(result.estimates) >= 1


def test_iraq_bundle_validates() -> None:
    result = load_and_validate_bundle(IRAQ_FIXTURE_DIR)

    assert result.conflict.conflict_id == "irq-war-occupation-2003-2011"
    assert len(result.episodes) >= 1
    assert all(episode.quality_tier in {None, "A", "B", "C", "D"} for episode in result.episodes)


def test_syria_bundle_validates_with_open_end_date_and_global_notes() -> None:
    result = load_and_validate_bundle(SYRIA_FIXTURE_DIR)

    assert result.conflict.conflict_id == "syria-civil-war-2011-present"
    assert result.conflict.end_date is None
    assert len(result.episodes) >= 1


def test_episode_can_be_open_ended_when_estimate_is_incomplete(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path, include_dr=True)
    episodes = json.loads((bundle_dir / "episodes.json").read_text(encoding="utf-8"))
    episodes[0]["full_estimate_completed"] = False
    episodes[0]["quality_tier"] = None
    episodes[0]["end_date"] = None
    (bundle_dir / "episodes.json").write_text(json.dumps(episodes, indent=2) + "\n", encoding="utf-8")

    estimates = json.loads((bundle_dir / "estimates.json").read_text(encoding="utf-8"))
    estimates = [estimate for estimate in estimates if estimate["metric_name"] != "dr_v1_direct"]
    (bundle_dir / "estimates.json").write_text(json.dumps(estimates, indent=2) + "\n", encoding="utf-8")

    result = load_and_validate_bundle(bundle_dir)
    assert result.episodes[0].end_date is None
    assert result.episodes[0].full_estimate_completed is False


def test_missing_claim_reference_fails(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path)
    estimates = json.loads((bundle_dir / "estimates.json").read_text(encoding="utf-8"))
    estimates[0]["input_claim_ids"] = ["MISSING-CLAIM-ID"]
    (bundle_dir / "estimates.json").write_text(json.dumps(estimates, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BundleValidationError, match="unknown claim ids"):
        load_and_validate_bundle(bundle_dir)


def test_countrywide_denominator_for_subnational_episode_fails(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path)
    claims = json.loads((bundle_dir / "claims.json").read_text(encoding="utf-8"))
    claims.append(
        {
            "claim_id": "CLM-BAD-DENOM",
            "episode_id": "EP-1",
            "source_id": "SRC-1",
            "variable_name": "civ_population_present",
            "population_class": "civilian",
            "death_type": "not_applicable",
            "start_date": "2020-01-01",
            "end_date": "2020-01-31",
            "geographic_scope": "Exampleland",
            "value_low": 1000000,
            "value_best": 1500000,
            "value_high": 2000000,
            "unit": "persons_present_average",
            "estimate_method": "source_direct",
            "excerpt": "Synthetic bad denominator for test.",
            "pages_or_sections": "n/a",
            "transform_note": "n/a",
            "confidence_note": "low"
        }
    )
    (bundle_dir / "claims.json").write_text(json.dumps(claims, indent=2) + "\n", encoding="utf-8")

    estimates = json.loads((bundle_dir / "estimates.json").read_text(encoding="utf-8"))
    for estimate in estimates:
        if estimate["metric_name"] == "civ_person_months":
            estimate["input_claim_ids"].append("CLM-BAD-DENOM")
    (bundle_dir / "estimates.json").write_text(json.dumps(estimates, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BundleValidationError, match="countrywide denominator claim"):
        load_and_validate_bundle(bundle_dir)


def test_country_named_denominator_for_subnational_episode_fails(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path)
    claims = json.loads((bundle_dir / "claims.json").read_text(encoding="utf-8"))
    claims.append(
        {
            "claim_id": "CLM-BAD-DENOM-COUNTRY",
            "episode_id": "EP-1",
            "source_id": "SRC-1",
            "variable_name": "civ_population_present",
            "population_class": "civilian",
            "death_type": "not_applicable",
            "start_date": "2020-01-01",
            "end_date": "2020-01-31",
            "geographic_scope": "Exampleland",
            "value_low": 1000000,
            "value_best": 1500000,
            "value_high": 2000000,
            "unit": "persons_present_average",
            "estimate_method": "source_direct",
            "excerpt": "Synthetic country-level denominator for test.",
            "pages_or_sections": "n/a",
            "transform_note": "n/a",
            "confidence_note": "low"
        }
    )
    (bundle_dir / "claims.json").write_text(json.dumps(claims, indent=2) + "\n", encoding="utf-8")

    estimates = json.loads((bundle_dir / "estimates.json").read_text(encoding="utf-8"))
    for estimate in estimates:
        if estimate["metric_name"] == "civ_person_months":
            estimate["input_claim_ids"] = ["CLM-BAD-DENOM-COUNTRY"]
    (bundle_dir / "estimates.json").write_text(json.dumps(estimates, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BundleValidationError, match="countrywide denominator claim"):
        load_and_validate_bundle(bundle_dir)


def test_low_best_high_ordering_fails(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path)
    claims = json.loads((bundle_dir / "claims.json").read_text(encoding="utf-8"))
    claims[0]["value_low"] = 500000
    claims[0]["value_best"] = 340000
    (bundle_dir / "claims.json").write_text(json.dumps(claims, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BundleValidationError, match="value_low must be <= value_best"):
        load_and_validate_bundle(bundle_dir)


def test_optional_side_attribution_fields_validate(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path)
    claims = json.loads((bundle_dir / "claims.json").read_text(encoding="utf-8"))
    claims[0]["victim_side"] = "Bosnian government-held Sarajevo"
    claims[0]["inflicting_side"] = "Bosnian Serb forces"
    (bundle_dir / "claims.json").write_text(json.dumps(claims, indent=2) + "\n", encoding="utf-8")

    estimates = json.loads((bundle_dir / "estimates.json").read_text(encoding="utf-8"))
    estimates[0]["victim_side"] = "Bosnian government-held Sarajevo"
    estimates[0]["inflicting_side"] = "Bosnian Serb forces"
    (bundle_dir / "estimates.json").write_text(json.dumps(estimates, indent=2) + "\n", encoding="utf-8")

    result = load_and_validate_bundle(bundle_dir)

    assert result.claims[0].victim_side == "Bosnian government-held Sarajevo"
    assert result.claims[0].inflicting_side == "Bosnian Serb forces"
    assert result.estimates[0].victim_side == "Bosnian government-held Sarajevo"
    assert result.estimates[0].inflicting_side == "Bosnian Serb forces"


def test_completed_episode_without_publishable_dr_fails(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path)
    estimates = json.loads((bundle_dir / "estimates.json").read_text(encoding="utf-8"))
    estimates = [estimate for estimate in estimates if estimate["metric_name"] != "dr_v1_direct"]
    (bundle_dir / "estimates.json").write_text(json.dumps(estimates, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BundleValidationError, match="full_estimate_completed but lacks a publishable DR or fallback estimate"):
        load_and_validate_bundle(bundle_dir)


def test_partial_episode_with_publishable_dr_fails(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path)
    episodes = json.loads((bundle_dir / "episodes.json").read_text(encoding="utf-8"))
    episodes[0]["full_estimate_completed"] = False
    (bundle_dir / "episodes.json").write_text(json.dumps(episodes, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BundleValidationError, match="publishes a DR or fallback estimate but is not marked full_estimate_completed"):
        load_and_validate_bundle(bundle_dir)


def test_null_placeholder_dr_row_fails(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path)
    estimates = json.loads((bundle_dir / "estimates.json").read_text(encoding="utf-8"))
    for estimate in estimates:
        if estimate["metric_name"] == "dr_v1_direct":
            estimate["value_low"] = None
            estimate["value_best"] = None
            estimate["value_high"] = None
    (bundle_dir / "estimates.json").write_text(json.dumps(estimates, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BundleValidationError, match="null placeholder dr_v1_direct"):
        load_and_validate_bundle(bundle_dir)


def test_publishable_dr_requires_publishable_person_month_components(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path)
    estimates = json.loads((bundle_dir / "estimates.json").read_text(encoding="utf-8"))
    for estimate in estimates:
        if estimate["metric_name"] == "civ_person_months":
            estimate["value_low"] = None
            estimate["value_best"] = None
            estimate["value_high"] = None
    (bundle_dir / "estimates.json").write_text(json.dumps(estimates, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BundleValidationError, match="publishes dr_v1_direct without publishable civ_person_months"):
        load_and_validate_bundle(bundle_dir)


def test_publishable_dr_must_match_component_formula(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path)
    result = load_and_validate_bundle(bundle_dir)

    dr_estimate = next(estimate for estimate in result.estimates if estimate.metric_name == "dr_v1_direct")
    assert dr_estimate.value_low == pytest.approx(10.204081632653061)
    assert dr_estimate.value_best == pytest.approx(20.0)
    assert dr_estimate.value_high == pytest.approx(42.0)


def test_inverted_dr_formula_fails(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path)
    estimates = json.loads((bundle_dir / "estimates.json").read_text(encoding="utf-8"))
    for estimate in estimates:
        if estimate["metric_name"] == "dr_v1_direct":
            estimate["value_low"] = 1 / 42
            estimate["value_best"] = 1 / 20
            estimate["value_high"] = 1 / 10.204081632653061
    (bundle_dir / "estimates.json").write_text(json.dumps(estimates, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BundleValidationError, match="civ_rate/mil_rate"):
        load_and_validate_bundle(bundle_dir)


def _copy_bundle(tmp_path: Path) -> Path:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    for path in FIXTURE_DIR.iterdir():
        if path.is_file():
            (bundle_dir / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return bundle_dir


def _write_synthetic_bundle(tmp_path: Path, *, include_dr: bool = True) -> Path:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    payload = {
        "conflict.json": {
            "conflict_id": "demo-conflict",
            "conflict_name": "Demo conflict",
            "aliases": [],
            "family_summary": "demo",
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "countries": ["Exampleland"],
            "regions": ["Example region"],
            "notes": "",
        },
        "episodes.json": [
            {
                "episode_id": "EP-1",
                "conflict_id": "demo-conflict",
                "episode_name": "Demo episode",
                "start_date": "2020-01-01",
                "end_date": "2020-01-31",
                "time_unit": "month",
                "geographic_scope": "Test city",
                "countries": ["Exampleland"],
                "admin_units": ["Test province", "Test city"],
                "theater_description": "demo theater",
                "geometry_method_note": "city bounded",
                "military_area_note": "city bounded",
                "civilian_area_note": "city bounded",
                "split_reason": "demo",
                "full_estimate_completed": True,
                "quality_tier": "B",
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
                "variables_supported": [
                    "mil_deaths_direct",
                    "civ_deaths_direct",
                    "mil_person_months",
                    "civ_person_months",
                ],
                "strengths": "demo",
                "limitations": "demo",
                "notes": "",
            }
        ],
        "claims.json": [
            {
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
                "excerpt": "Demo claim",
                "pages_or_sections": "p. 1",
                "transform_note": "",
                "confidence_note": "medium",
            },
            {
                "claim_id": "CLM-2",
                "episode_id": "EP-1",
                "source_id": "SRC-1",
                "variable_name": "civ_deaths_direct",
                "population_class": "civilian",
                "death_type": "direct",
                "start_date": "2020-01-01",
                "end_date": "2020-01-31",
                "geographic_scope": "Test city",
                "value_low": 5,
                "value_best": 6,
                "value_high": 7,
                "unit": "deaths",
                "estimate_method": "source_direct",
                "excerpt": "Demo claim",
                "pages_or_sections": "p. 1",
                "transform_note": "",
                "confidence_note": "medium",
            },
            {
                "claim_id": "CLM-3",
                "episode_id": "EP-1",
                "source_id": "SRC-1",
                "variable_name": "mil_person_months",
                "population_class": "military",
                "death_type": "not_applicable",
                "start_date": "2020-01-01",
                "end_date": "2020-01-31",
                "geographic_scope": "Test city",
                "value_low": 100,
                "value_best": 120,
                "value_high": 140,
                "unit": "person_months",
                "estimate_method": "source_direct",
                "excerpt": "Demo claim",
                "pages_or_sections": "p. 1",
                "transform_note": "",
                "confidence_note": "medium",
            },
            {
                "claim_id": "CLM-4",
                "episode_id": "EP-1",
                "source_id": "SRC-1",
                "variable_name": "civ_person_months",
                "population_class": "civilian",
                "death_type": "not_applicable",
                "start_date": "2020-01-01",
                "end_date": "2020-01-31",
                "geographic_scope": "Test city",
                "value_low": 1000,
                "value_best": 1200,
                "value_high": 1400,
                "unit": "person_months",
                "estimate_method": "source_direct",
                "excerpt": "Demo claim",
                "pages_or_sections": "p. 1",
                "transform_note": "",
                "confidence_note": "medium",
            },
        ],
        "estimates.json": [
            {
                "estimate_id": "EST-1",
                "episode_id": "EP-1",
                "metric_name": "mil_deaths_direct",
                "value_low": 10,
                "value_best": 12,
                "value_high": 15,
                "unit": "deaths",
                "estimate_method": "derived_from_sources",
                "input_claim_ids": ["CLM-1"],
                "formula_note": "demo",
                "uncertainty_note": "demo",
                "unknown_status_rule": "strict",
                "quality_tier": "B",
                "quality_note": "demo",
            },
            {
                "estimate_id": "EST-2",
                "episode_id": "EP-1",
                "metric_name": "civ_deaths_direct",
                "value_low": 5,
                "value_best": 6,
                "value_high": 7,
                "unit": "deaths",
                "estimate_method": "derived_from_sources",
                "input_claim_ids": ["CLM-2"],
                "formula_note": "demo",
                "uncertainty_note": "demo",
                "unknown_status_rule": "strict",
                "quality_tier": "B",
                "quality_note": "demo",
            },
            {
                "estimate_id": "EST-3",
                "episode_id": "EP-1",
                "metric_name": "mil_person_months",
                "value_low": 100,
                "value_best": 120,
                "value_high": 140,
                "unit": "person_months",
                "estimate_method": "derived_from_sources",
                "input_claim_ids": ["CLM-3"],
                "formula_note": "demo",
                "uncertainty_note": "demo",
                "unknown_status_rule": "not_applicable",
                "quality_tier": "B",
                "quality_note": "demo",
            },
            {
                "estimate_id": "EST-4",
                "episode_id": "EP-1",
                "metric_name": "civ_person_months",
                "value_low": 1000,
                "value_best": 1200,
                "value_high": 1400,
                "unit": "person_months",
                "estimate_method": "derived_from_sources",
                "input_claim_ids": ["CLM-4"],
                "formula_note": "demo",
                "uncertainty_note": "demo",
                "unknown_status_rule": "not_applicable",
                "quality_tier": "B",
                "quality_note": "demo",
            },
        ],
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
    if include_dr:
        payload["estimates.json"].append(
            {
                "estimate_id": "EST-5",
                "episode_id": "EP-1",
                "metric_name": "dr_v1_direct",
                "value_low": 10.204081632653061,
                "value_best": 20.0,
                "value_high": 42.0,
                "unit": "ratio",
                "estimate_method": "derived_from_sources",
                "input_claim_ids": ["CLM-1", "CLM-2", "CLM-3", "CLM-4"],
                "formula_note": "demo",
                "uncertainty_note": "demo",
                "unknown_status_rule": "strict",
                "quality_tier": "B",
                "quality_note": "demo",
            }
        )

    for filename, content in payload.items():
        (bundle_dir / filename).write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
    return bundle_dir
