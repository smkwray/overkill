from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


PopulationClass = Literal["military", "civilian", "unknown"]
DeathType = Literal["direct", "indirect", "not_applicable"]
EstimateMethod = Literal["source_direct", "derived_from_sources", "model_generated"]
UnknownStatusRule = Literal["strict", "proportional", "case_specific", "not_applicable"]
QualityTier = Literal["A", "B", "C", "D"]
TimeUnit = Literal["month", "quarter"]
AssumptionCategory = Literal[
    "geometry",
    "displacement",
    "troop_strength",
    "casualty_status",
    "time_interpolation",
    "other",
]
Sensitivity = Literal["low", "medium", "high"]


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _validate_interval(low: float | int | None, best: float | int | None, high: float | int | None) -> None:
    values = [("low", low), ("best", best), ("high", high)]
    present = [(name, value) for name, value in values if value is not None]
    if not present:
        return
    for name, value in present:
        if isinstance(value, (int, float)) and value < 0:
            raise ValueError(f"{name} must be >= 0")
    if low is not None and best is not None and low > best:
        raise ValueError("value_low must be <= value_best")
    if best is not None and high is not None and best > high:
        raise ValueError("value_best must be <= value_high")
    if low is not None and high is not None and low > high:
        raise ValueError("value_low must be <= value_high")


class Conflict(StrictBaseModel):
    conflict_id: str
    conflict_name: str
    aliases: list[str] = Field(default_factory=list)
    family_summary: str
    start_date: date
    end_date: date | None
    countries: list[str]
    regions: list[str]
    notes: str = ""

    @model_validator(mode="after")
    def validate_dates(self) -> "Conflict":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("conflict end_date must be >= start_date")
        return self


class Episode(StrictBaseModel):
    episode_id: str
    conflict_id: str
    episode_name: str
    start_date: date
    end_date: date | None
    time_unit: TimeUnit
    geographic_scope: str
    countries: list[str]
    admin_units: list[str]
    theater_description: str
    geometry_method_note: str
    military_area_note: str
    civilian_area_note: str
    split_reason: str
    full_estimate_completed: bool
    quality_tier: QualityTier | None
    quality_note: str

    @model_validator(mode="after")
    def validate_dates(self) -> "Episode":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("episode end_date must be >= start_date")
        if self.full_estimate_completed and self.quality_tier is None:
            raise ValueError("completed episodes must declare quality_tier")
        return self


class Source(StrictBaseModel):
    source_id: str
    citation_short: str
    title: str
    author_or_org: str
    year: str
    source_type: str
    url: HttpUrl | str | None
    pages_or_sections: str
    geographic_scope: str
    date_scope: str
    variables_supported: list[str]
    strengths: str
    limitations: str
    notes: str = ""


class Claim(StrictBaseModel):
    claim_id: str
    episode_id: str
    source_id: str
    variable_name: str
    population_class: PopulationClass
    victim_side: str | None = None
    inflicting_side: str | None = None
    death_type: DeathType
    start_date: date
    end_date: date
    geographic_scope: str
    value_low: float | int | None
    value_best: float | int | None
    value_high: float | int | None
    unit: str
    estimate_method: EstimateMethod
    excerpt: str
    pages_or_sections: str
    transform_note: str
    confidence_note: str

    @model_validator(mode="after")
    def validate_claim(self) -> "Claim":
        if self.end_date < self.start_date:
            raise ValueError("claim end_date must be >= start_date")
        _validate_interval(self.value_low, self.value_best, self.value_high)
        return self


class Estimate(StrictBaseModel):
    estimate_id: str
    episode_id: str
    metric_name: str
    victim_side: str | None = None
    inflicting_side: str | None = None
    value_low: float | int | None
    value_best: float | int | None
    value_high: float | int | None
    unit: str
    estimate_method: EstimateMethod
    input_claim_ids: list[str]
    formula_note: str
    uncertainty_note: str
    unknown_status_rule: UnknownStatusRule
    quality_tier: QualityTier
    quality_note: str

    @model_validator(mode="after")
    def validate_estimate(self) -> "Estimate":
        _validate_interval(self.value_low, self.value_best, self.value_high)
        if self.metric_name.endswith("_direct") and not self.estimate_method:
            raise ValueError("direct-death estimates must declare estimate_method")
        if self.metric_name == "dr_v1_direct" and not self.input_claim_ids:
            raise ValueError("dr_v1_direct requires input_claim_ids")
        return self


class Assumption(StrictBaseModel):
    assumption_id: str
    episode_id: str | None
    category: AssumptionCategory
    assumption_text: str
    rationale: str
    sensitivity: Sensitivity


class OpenQuestion(StrictBaseModel):
    episode_id: str | None
    question: str
    why_it_matters: str
    what_would_resolve_it: str
