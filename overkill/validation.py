from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from overkill.models import Assumption, Claim, Conflict, Episode, Estimate, OpenQuestion, Source


REQUIRED_BUNDLE_FILES = {
    "conflict.json",
    "episodes.json",
    "sources.json",
    "claims.json",
    "estimates.json",
    "assumptions.json",
    "open_questions.json",
}


class BundleValidationError(Exception):
    """Raised when a research bundle fails contract validation."""


@dataclass(slots=True)
class BundleValidationResult:
    bundle_path: Path
    conflict: Conflict
    episodes: list[Episode]
    sources: list[Source]
    claims: list[Claim]
    estimates: list[Estimate]
    assumptions: list[Assumption]
    open_questions: list[OpenQuestion]


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _ensure_required_files(bundle_path: Path) -> None:
    missing = sorted(name for name in REQUIRED_BUNDLE_FILES if not (bundle_path / name).is_file())
    if missing:
        raise BundleValidationError(f"bundle is missing required files: {', '.join(missing)}")


def _ensure_unique_ids(items: list[Any], attr: str, label: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        value = getattr(item, attr)
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        dupes = ", ".join(sorted(duplicates))
        raise BundleValidationError(f"duplicate {label} ids: {dupes}")


def _scope_is_subnational(scope: str) -> bool:
    lowered = scope.lower()
    return any(token in lowered for token in ["subnational", "urban", "siege", "enclave", "corridor", "city"])


def _claim_is_population_or_person_month_input(claim: Claim) -> bool:
    variable_name = claim.variable_name.lower()
    return "population" in variable_name or "person_month" in variable_name


def _normalize_scope_text(value: str) -> str:
    return " ".join(value.lower().replace("-", " ").replace("/", " ").split())


def _episode_scope_explicitly_covers_claim_scope(episode: Episode, claim_scope: str) -> bool:
    episode_fields = [episode.geographic_scope, episode.theater_description, episode.civilian_area_note, episode.military_area_note]
    episode_fields.extend(episode.admin_units)
    normalized_fields = [_normalize_scope_text(value) for value in episode_fields if value]
    return any(claim_scope in value for value in normalized_fields)


def _claim_scope_is_countrywide_for_episode(claim: Claim, conflict: Conflict, episode: Episode) -> bool:
    claim_scope = _normalize_scope_text(claim.geographic_scope)
    if any(token in claim_scope for token in ("nationwide", "countrywide", "whole country", "entire country", "national")):
        return True

    normalized_countries = {_normalize_scope_text(country) for country in conflict.countries}
    if claim_scope in normalized_countries and not _episode_scope_explicitly_covers_claim_scope(episode, claim_scope):
        return True

    return any(claim_scope in {f"{country} wide", f"{country} countrywide", f"{country} nationwide"} for country in normalized_countries)


def _estimate_has_publishable_values(estimate: Estimate) -> bool:
    return any(value is not None for value in (estimate.value_low, estimate.value_best, estimate.value_high))


def _select_metric_estimate(estimates: list[Estimate], target: Estimate, metric_name: str) -> Estimate | None:
    candidates = [
        estimate
        for estimate in estimates
        if estimate.episode_id == target.episode_id
        and estimate.metric_name == metric_name
        and _estimate_has_publishable_values(estimate)
    ]
    if not candidates:
        return None

    exact_side_match = [
        estimate
        for estimate in candidates
        if estimate.victim_side == target.victim_side and estimate.inflicting_side == target.inflicting_side
    ]
    if len(exact_side_match) == 1:
        return exact_side_match[0]

    generic_match = [
        estimate for estimate in candidates if estimate.victim_side is None and estimate.inflicting_side is None
    ]
    if len(generic_match) == 1:
        return generic_match[0]

    if len(candidates) == 1:
        return candidates[0]

    return None


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    if numerator < 0 or denominator <= 0:
        return None
    return numerator / denominator


def _expected_dr_bounds(
    mil_deaths: Estimate,
    civ_deaths: Estimate,
    mil_person_months: Estimate,
    civ_person_months: Estimate,
) -> tuple[float | None, float | None, float | None]:
    low_mil_rate = _safe_ratio(mil_deaths.value_low, mil_person_months.value_high)
    best_mil_rate = _safe_ratio(mil_deaths.value_best, mil_person_months.value_best)
    high_mil_rate = _safe_ratio(mil_deaths.value_high, mil_person_months.value_low)

    high_civ_rate = _safe_ratio(civ_deaths.value_high, civ_person_months.value_low)
    best_civ_rate = _safe_ratio(civ_deaths.value_best, civ_person_months.value_best)
    low_civ_rate = _safe_ratio(civ_deaths.value_low, civ_person_months.value_high)

    low = _safe_ratio(low_mil_rate, high_civ_rate)
    best = _safe_ratio(best_mil_rate, best_civ_rate)
    high = _safe_ratio(high_mil_rate, low_civ_rate)
    return low, best, high


def _bound_matches(actual: float, expected: float, *, rel_tol: float = 0.05, abs_tol: float = 1e-9) -> bool:
    return math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=abs_tol)


def _validate_dr_formula_consistency(estimates: list[Estimate], dr_estimate: Estimate) -> None:
    mil_deaths = _select_metric_estimate(estimates, dr_estimate, "mil_deaths_direct")
    civ_deaths = _select_metric_estimate(estimates, dr_estimate, "civ_deaths_direct")
    mil_person_months = _select_metric_estimate(estimates, dr_estimate, "mil_person_months")
    civ_person_months = _select_metric_estimate(estimates, dr_estimate, "civ_person_months")
    if not all((mil_deaths, civ_deaths, mil_person_months, civ_person_months)):
        return

    expected_low, expected_best, expected_high = _expected_dr_bounds(
        mil_deaths=mil_deaths,
        civ_deaths=civ_deaths,
        mil_person_months=mil_person_months,
        civ_person_months=civ_person_months,
    )

    comparisons = [
        ("low", dr_estimate.value_low, expected_low),
        ("best", dr_estimate.value_best, expected_best),
        ("high", dr_estimate.value_high, expected_high),
    ]
    mismatches: list[str] = []
    for label, actual, expected in comparisons:
        if actual is None or expected is None:
            continue
        if not _bound_matches(actual, expected):
            mismatches.append(f"{label} actual={actual} expected={expected:.12g}")

    if not mismatches:
        return

    likely_inverted = False
    if dr_estimate.value_best is not None and expected_best not in (None, 0):
        likely_inverted = _bound_matches(dr_estimate.value_best, 1 / expected_best)

    message = (
        f"estimate {dr_estimate.estimate_id} publishes dr_v1_direct inconsistent with component estimates: "
        + "; ".join(mismatches)
    )
    if likely_inverted:
        message += " (best bound looks like civ_rate/mil_rate rather than mil_rate/civ_rate)"
    raise BundleValidationError(message)


def _episode_has_publishable_ratio(estimates: list[Estimate], episode_id: str) -> bool:
    return any(
        estimate.episode_id == episode_id
        and estimate.metric_name in {"dr_v1_direct", "dr_midpoint_fallback"}
        and _estimate_has_publishable_values(estimate)
        for estimate in estimates
    )


def _episode_has_metric_with_values(estimates: list[Estimate], episode_id: str, metric_name: str) -> bool:
    return any(
        estimate.episode_id == episode_id
        and estimate.metric_name == metric_name
        and _estimate_has_publishable_values(estimate)
        for estimate in estimates
    )


def _validate_cross_references(
    conflict: Conflict,
    episodes: list[Episode],
    sources: list[Source],
    claims: list[Claim],
    estimates: list[Estimate],
    assumptions: list[Assumption],
    open_questions: list[OpenQuestion],
) -> None:
    episode_ids = {episode.episode_id for episode in episodes}
    source_ids = {source.source_id for source in sources}
    claim_ids = {claim.claim_id for claim in claims}

    for episode in episodes:
        if episode.conflict_id != conflict.conflict_id:
            raise BundleValidationError(
                f"episode {episode.episode_id} references conflict_id={episode.conflict_id}, expected {conflict.conflict_id}"
            )
        if episode.full_estimate_completed and not episode.quality_tier:
            raise BundleValidationError(f"episode {episode.episode_id} lacks quality_tier")

    for claim in claims:
        if claim.episode_id not in episode_ids:
            raise BundleValidationError(f"claim {claim.claim_id} references unknown episode_id={claim.episode_id}")
        if claim.source_id not in source_ids:
            raise BundleValidationError(f"claim {claim.claim_id} references unknown source_id={claim.source_id}")

    for estimate in estimates:
        if estimate.episode_id not in episode_ids:
            raise BundleValidationError(f"estimate {estimate.estimate_id} references unknown episode_id={estimate.episode_id}")
        missing_claim_ids = [claim_id for claim_id in estimate.input_claim_ids if claim_id not in claim_ids]
        if missing_claim_ids:
            raise BundleValidationError(
                f"estimate {estimate.estimate_id} references unknown claim ids: {', '.join(missing_claim_ids)}"
            )
        if estimate.metric_name.endswith("_direct") and estimate.metric_name != "unknown_deaths_direct" and not estimate.input_claim_ids:
            raise BundleValidationError(f"estimate {estimate.estimate_id} must reference input_claim_ids")
        if estimate.metric_name.endswith("_direct") and not estimate.estimate_method:
            raise BundleValidationError(f"estimate {estimate.estimate_id} lacks estimate_method")
        if estimate.metric_name == "dr_v1_direct" and estimate.unknown_status_rule == "not_applicable":
            raise BundleValidationError(f"estimate {estimate.estimate_id} must specify unknown_status_rule")

    for assumption in assumptions:
        if assumption.episode_id is not None and assumption.episode_id not in episode_ids:
            raise BundleValidationError(
                f"assumption {assumption.assumption_id} references unknown episode_id={assumption.episode_id}"
            )

    for question in open_questions:
        if question.episode_id is not None and question.episode_id not in episode_ids:
            raise BundleValidationError(f"open question references unknown episode_id={question.episode_id}")


def _validate_semantics(conflict: Conflict, episodes: list[Episode], claims: list[Claim], estimates: list[Estimate]) -> None:
    claims_by_id = {claim.claim_id: claim for claim in claims}
    episodes_by_id = {episode.episode_id: episode for episode in episodes}

    for estimate in estimates:
        if estimate.metric_name in {"dr_v1_direct", "dr_midpoint_fallback"} and not _estimate_has_publishable_values(estimate):
            raise BundleValidationError(
                f"estimate {estimate.estimate_id} is a null placeholder {estimate.metric_name}; omit it instead of publishing all-null values"
            )

    for episode in episodes:
        has_publishable_ratio = _episode_has_publishable_ratio(estimates, episode.episode_id)
        if episode.full_estimate_completed and not has_publishable_ratio:
            raise BundleValidationError(
                f"episode {episode.episode_id} is marked full_estimate_completed but lacks a publishable DR or fallback estimate"
            )
        if not episode.full_estimate_completed and has_publishable_ratio:
            raise BundleValidationError(
                f"episode {episode.episode_id} publishes a DR or fallback estimate but is not marked full_estimate_completed"
            )

    for estimate in estimates:
        if estimate.metric_name == "dr_v1_direct":
            required_metrics = {
                "mil_deaths_direct",
                "civ_deaths_direct",
            }
            metric_names = {other.metric_name for other in estimates if other.episode_id == estimate.episode_id}
            missing = required_metrics - metric_names
            if missing:
                raise BundleValidationError(
                    f"episode {estimate.episode_id} publishes dr_v1_direct without component estimates: {', '.join(sorted(missing))}"
                )
            if _estimate_has_publishable_values(estimate):
                for required_metric in ("mil_deaths_direct", "civ_deaths_direct", "mil_person_months", "civ_person_months"):
                    if not _episode_has_metric_with_values(estimates, estimate.episode_id, required_metric):
                        raise BundleValidationError(
                            f"episode {estimate.episode_id} publishes dr_v1_direct without publishable {required_metric}"
                        )
                _validate_dr_formula_consistency(estimates, estimate)

        if estimate.metric_name == "dr_midpoint_fallback" and _estimate_has_publishable_values(estimate):
            for required_metric in ("mil_deaths_direct", "civ_deaths_direct"):
                if not _episode_has_metric_with_values(estimates, estimate.episode_id, required_metric):
                    raise BundleValidationError(
                        f"episode {estimate.episode_id} publishes dr_midpoint_fallback without publishable {required_metric}"
                    )

        if estimate.metric_name in {"mil_person_months", "civ_person_months"}:
            episode = episodes_by_id[estimate.episode_id]
            if _scope_is_subnational(episode.geographic_scope):
                for claim_id in estimate.input_claim_ids:
                    claim = claims_by_id[claim_id]
                    if not _claim_is_population_or_person_month_input(claim):
                        continue
                    if _claim_scope_is_countrywide_for_episode(claim, conflict, episode):
                        raise BundleValidationError(
                            f"estimate {estimate.estimate_id} uses countrywide denominator claim {claim.claim_id} for subnational episode {estimate.episode_id}"
                        )


def load_and_validate_bundle(bundle_path: str | Path) -> BundleValidationResult:
    path = Path(bundle_path)
    if not path.is_dir():
        raise BundleValidationError(f"bundle path is not a directory: {path}")

    _ensure_required_files(path)

    try:
        conflict = Conflict.model_validate(_read_json(path / "conflict.json"))
        episodes = [Episode.model_validate(item) for item in _read_json(path / "episodes.json")]
        sources = [Source.model_validate(item) for item in _read_json(path / "sources.json")]
        claims = [Claim.model_validate(item) for item in _read_json(path / "claims.json")]
        estimates = [Estimate.model_validate(item) for item in _read_json(path / "estimates.json")]
        assumptions = [Assumption.model_validate(item) for item in _read_json(path / "assumptions.json")]
        open_questions = [OpenQuestion.model_validate(item) for item in _read_json(path / "open_questions.json")]
    except ValidationError as exc:
        raise BundleValidationError(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise BundleValidationError(f"invalid JSON in {exc.msg}") from exc

    _ensure_unique_ids(episodes, "episode_id", "episode")
    _ensure_unique_ids(sources, "source_id", "source")
    _ensure_unique_ids(claims, "claim_id", "claim")
    _ensure_unique_ids(estimates, "estimate_id", "estimate")
    _ensure_unique_ids(assumptions, "assumption_id", "assumption")

    _validate_cross_references(conflict, episodes, sources, claims, estimates, assumptions, open_questions)
    _validate_semantics(conflict, episodes, claims, estimates)

    return BundleValidationResult(
        bundle_path=path,
        conflict=conflict,
        episodes=episodes,
        sources=sources,
        claims=claims,
        estimates=estimates,
        assumptions=assumptions,
        open_questions=open_questions,
    )
