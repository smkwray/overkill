from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from overkill.validation import BundleValidationError, load_and_validate_bundle


FIXTURE_DIR = Path("tests/fixtures/bundles/demo-conflict")


def test_fixture_bundle_validates() -> None:
    result = load_and_validate_bundle(FIXTURE_DIR)

    assert result.conflict.conflict_id == "demo-conflict"
    assert len(result.episodes) == 1
    assert {estimate.metric_name for estimate in result.estimates} >= {"dr_v1_direct", "civ_person_months"}


def test_ongoing_conflict_validates_without_end_date(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path)
    conflict = json.loads((bundle_dir / "conflict.json").read_text(encoding="utf-8"))
    conflict["end_date"] = None
    (bundle_dir / "conflict.json").write_text(json.dumps(conflict, indent=2) + "\n", encoding="utf-8")

    result = load_and_validate_bundle(bundle_dir)

    assert result.conflict.end_date is None


def test_episode_can_be_open_ended_when_estimate_is_incomplete(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path)
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


def test_countrywide_military_denominator_for_subnational_episode_fails(tmp_path: Path) -> None:
    bundle_dir = _write_synthetic_bundle(tmp_path)
    claims = json.loads((bundle_dir / "claims.json").read_text(encoding="utf-8"))
    claims.append(
        {
            "claim_id": "CLM-BAD-MIL-DENOM",
            "episode_id": "EP-1",
            "source_id": "SRC-1",
            "variable_name": "mil_population_present",
            "population_class": "military",
            "death_type": "not_applicable",
            "start_date": "2020-01-01",
            "end_date": "2020-01-31",
            "geographic_scope": "Exampleland",
            "value_low": 50000,
            "value_best": 60000,
            "value_high": 70000,
            "unit": "persons_present_average",
            "estimate_method": "source_direct",
            "excerpt": "Synthetic countrywide military denominator for test.",
            "pages_or_sections": "n/a",
            "transform_note": "n/a",
            "confidence_note": "low",
        }
    )
    (bundle_dir / "claims.json").write_text(json.dumps(claims, indent=2) + "\n", encoding="utf-8")

    estimates = json.loads((bundle_dir / "estimates.json").read_text(encoding="utf-8"))
    for estimate in estimates:
        if estimate["metric_name"] == "mil_person_months":
            estimate["input_claim_ids"].append("CLM-BAD-MIL-DENOM")
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


def _write_synthetic_bundle(tmp_path: Path) -> Path:
    bundle_dir = tmp_path / "bundle"
    shutil.copytree(FIXTURE_DIR, bundle_dir)
    return bundle_dir
