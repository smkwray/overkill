from __future__ import annotations

import json
import re
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from overkill.models import Assumption, Claim, Conflict, Episode, Estimate, OpenQuestion, Source
from overkill.validation import BundleValidationError, load_and_validate_bundle


REQUIRED_JSON_FILES = [
    "conflict.json",
    "episodes.json",
    "sources.json",
    "claims.json",
    "estimates.json",
    "assumptions.json",
    "open_questions.json",
]

_REQUIRED_FILE_SET = set(REQUIRED_JSON_FILES)
_FILE_NAME_PATTERN = "|".join(re.escape(name) for name in REQUIRED_JSON_FILES)
_HEADING_WITH_BLOCK_NAME_RE = re.compile(rf"(?mi)^#{{1,6}}[^\n]*?(?P<name>{_FILE_NAME_PATTERN})[^\n]*$")
_JSON_FENCE_RE = re.compile(r"(?is)```(?:json|[A-Za-z0-9_.-]+)?\s*(?P<body>.*?)\s*```")

_NORMALIZATION_FIELDS = {
    "conflict.json": set(Conflict.model_fields.keys()),
    "episodes.json": set(Episode.model_fields.keys()),
    "sources.json": set(Source.model_fields.keys()),
    "claims.json": set(Claim.model_fields.keys()),
    "estimates.json": set(Estimate.model_fields.keys()),
    "assumptions.json": set(Assumption.model_fields.keys()),
    "open_questions.json": set(OpenQuestion.model_fields.keys()),
}

_ASSUMPTION_CATEGORY_ALIASES = {
    "population": "displacement",
    "civilian_denominator": "displacement",
    "military_denominator": "troop_strength",
    "status_mix": "casualty_status",
    "scope": "geometry",
    "counting_rule": "other",
    "side_attribution": "casualty_status",
    "status_classification": "casualty_status",
    "evidence_quality": "other",
}

_QUALITY_TIER_ALIASES = {
    "low": "D",
    "low_medium": "C",
    "low-medium": "C",
    "medium-low": "C",
    "medium_low": "C",
    "medium": "C",
    "medium-high": "B",
    "medium_high": "B",
    "high": "A",
    "c+": "C",
    "b-": "B",
    "b+": "B",
    "a-": "A",
}

_POPULATION_CLASS_ALIASES = {
    "total": "unknown",
    "military_or_armed": "military",
}

_VALID_ESTIMATE_METHODS = {"source_direct", "derived_from_sources", "model_generated"}
_VALID_UNKNOWN_STATUS_RULES = {"strict", "proportional", "case_specific", "not_applicable"}


@dataclass(slots=True)
class ParsedMarkdownBundle:
    source_path: Path
    markdown_text: str
    conflict_id: str
    slug: str | None
    payloads: dict[str, dict[str, Any] | list[dict[str, Any]]]
    mtime: float
    is_copy_name: bool


@dataclass(slots=True)
class IngestRecord:
    conflict_id: str
    source_path: str
    bundle_path: str | None = None
    reason: str | None = None
    kept_source_path: str | None = None


@dataclass(slots=True)
class IngestSummary:
    created: list[IngestRecord] = field(default_factory=list)
    skipped_existing: list[IngestRecord] = field(default_factory=list)
    skipped_duplicate_inputs: list[IngestRecord] = field(default_factory=list)
    failed_parse: list[IngestRecord] = field(default_factory=list)
    failed_validation: list[IngestRecord] = field(default_factory=list)
    failed_write: list[IngestRecord] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.failed_parse) + len(self.failed_validation) + len(self.failed_write)

    def as_dict(self) -> dict[str, Any]:
        return {
            "created": [asdict(record) for record in self.created],
            "skipped_existing": [asdict(record) for record in self.skipped_existing],
            "skipped_duplicate_inputs": [asdict(record) for record in self.skipped_duplicate_inputs],
            "failed_parse": [asdict(record) for record in self.failed_parse],
            "failed_validation": [asdict(record) for record in self.failed_validation],
            "failed_write": [asdict(record) for record in self.failed_write],
            "error_count": self.error_count,
        }


def expand_markdown_inputs(
    inputs: list[Path],
    *,
    pattern: str = "overkill_*_research_bundle*.md",
) -> list[Path]:
    """Expand file and directory inputs into a de-duplicated ordered markdown file list."""
    expanded: list[Path] = []
    seen: set[Path] = set()

    for item in inputs:
        path = Path(item)
        if path.is_dir():
            candidates = sorted(path.glob(pattern))
        elif path.is_file():
            candidates = [path]
        else:
            raise ValueError(f"input path does not exist: {path}")

        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            expanded.append(candidate)

    return expanded


def import_markdown_bundles(
    markdown_files: list[Path],
    *,
    bundles_root: Path = Path("research/input/gptpro"),
    overwrite: bool = False,
    validate: bool = True,
) -> IngestSummary:
    summary = IngestSummary()
    parsed_by_conflict: dict[str, list[ParsedMarkdownBundle]] = {}

    for path in markdown_files:
        try:
            parsed = _parse_markdown_bundle(path)
        except Exception as exc:  # pragma: no cover - explicit summary path
            summary.failed_parse.append(
                IngestRecord(
                    conflict_id="unknown",
                    source_path=str(path),
                    reason=str(exc),
                )
            )
            continue
        parsed_by_conflict.setdefault(parsed.conflict_id, []).append(parsed)

    bundles_root.mkdir(parents=True, exist_ok=True)

    for conflict_id, items in sorted(parsed_by_conflict.items()):
        chosen = _choose_preferred_item(items)
        for item in items:
            if item.source_path == chosen.source_path:
                continue
            summary.skipped_duplicate_inputs.append(
                IngestRecord(
                    conflict_id=conflict_id,
                    source_path=str(item.source_path),
                    kept_source_path=str(chosen.source_path),
                    reason="duplicate input for same conflict_id",
                )
            )

        target_dir = bundles_root / conflict_id
        if target_dir.exists() and not overwrite:
            summary.skipped_existing.append(
                IngestRecord(
                    conflict_id=conflict_id,
                    source_path=str(chosen.source_path),
                    bundle_path=str(target_dir),
                    reason="target bundle directory already exists; skipped without overwrite",
                )
            )
            continue

        try:
            _materialize_bundle(chosen, target_dir, overwrite=overwrite, validate=validate)
        except BundleValidationError as exc:
            summary.failed_validation.append(
                IngestRecord(
                    conflict_id=conflict_id,
                    source_path=str(chosen.source_path),
                    bundle_path=str(target_dir),
                    reason=str(exc),
                )
            )
            continue
        except Exception as exc:  # pragma: no cover - explicit summary path
            summary.failed_write.append(
                IngestRecord(
                    conflict_id=conflict_id,
                    source_path=str(chosen.source_path),
                    bundle_path=str(target_dir),
                    reason=str(exc),
                )
            )
            continue

        summary.created.append(
            IngestRecord(
                conflict_id=conflict_id,
                source_path=str(chosen.source_path),
                bundle_path=str(target_dir),
            )
        )

    return summary


def _choose_preferred_item(items: list[ParsedMarkdownBundle]) -> ParsedMarkdownBundle:
    # Prefer non-(1) filenames, then newer file timestamps.
    return sorted(items, key=lambda item: (item.is_copy_name, -item.mtime, item.source_path.name.lower()))[0]


def _materialize_bundle(
    parsed: ParsedMarkdownBundle,
    target_dir: Path,
    *,
    overwrite: bool,
    validate: bool,
) -> None:
    temp_dir = target_dir.parent / f".tmp_ingest_{parsed.conflict_id}_{uuid.uuid4().hex[:8]}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=False)

    try:
        for filename in REQUIRED_JSON_FILES:
            payload = parsed.payloads[filename]
            (temp_dir / filename).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        (temp_dir / "raw-response.md").write_text(parsed.markdown_text, encoding="utf-8")
        slug = parsed.slug or _derive_slug_from_filename(parsed.source_path)
        (temp_dir / f"overkill_{slug}_research_bundle.md").write_text(parsed.markdown_text, encoding="utf-8")

        if validate:
            load_and_validate_bundle(temp_dir)

        if overwrite and target_dir.exists():
            shutil.rmtree(target_dir)

        temp_dir.replace(target_dir)
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise


def _parse_markdown_bundle(path: Path) -> ParsedMarkdownBundle:
    if not path.exists() or not path.is_file():
        raise ValueError(f"markdown input is not a file: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = _extract_json_blocks(text)

    missing = sorted(_REQUIRED_FILE_SET - set(blocks))
    if missing:
        raise ValueError(f"missing required JSON blocks: {', '.join(missing)}")

    payloads: dict[str, dict[str, Any] | list[dict[str, Any]]] = {}
    for filename in REQUIRED_JSON_FILES:
        try:
            raw_payload = json.loads(blocks[filename])
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON for {filename}: {exc}") from exc
        payloads[filename] = _normalize_payload(filename, raw_payload)

    _reconcile_episode_completion_flags(payloads)
    _drop_non_publishable_dr_estimates(payloads)

    conflict = payloads["conflict.json"]
    if not isinstance(conflict, dict):
        raise ValueError("conflict.json must be an object")

    conflict_id = conflict.get("conflict_id")
    if not isinstance(conflict_id, str) or not conflict_id.strip():
        raise ValueError("conflict.json missing required conflict_id")

    slug = conflict.get("slug")
    slug_value = slug if isinstance(slug, str) and slug.strip() else None

    stat = path.stat()
    return ParsedMarkdownBundle(
        source_path=path,
        markdown_text=text,
        conflict_id=conflict_id,
        slug=slug_value,
        payloads=payloads,
        mtime=stat.st_mtime,
        is_copy_name="(1)" in path.name,
    )


def _extract_json_blocks(markdown_text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    headings = list(_HEADING_WITH_BLOCK_NAME_RE.finditer(markdown_text))
    for index, heading in enumerate(headings):
        name = heading.group("name")
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(markdown_text)
        section = markdown_text[start:end]
        fence = _JSON_FENCE_RE.search(section)
        if fence:
            blocks[name] = fence.group("body").strip()
    return blocks


def _normalize_payload(filename: str, data: Any) -> dict[str, Any] | list[dict[str, Any]]:
    allowed = _NORMALIZATION_FIELDS[filename]

    if filename == "conflict.json":
        if not isinstance(data, dict):
            raise ValueError("conflict.json must decode to an object")
        normalized = {key: value for key, value in data.items() if key in allowed}
        if normalized.get("end_date") == "":
            normalized["end_date"] = None
        return normalized

    if not isinstance(data, list):
        raise ValueError(f"{filename} must decode to an array")

    cleaned: list[dict[str, Any]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"{filename}[{index}] must be an object")
        normalized = {key: value for key, value in item.items() if key in allowed}

        if filename == "claims.json":
            population_class = normalized.get("population_class")
            if isinstance(population_class, str):
                normalized["population_class"] = _POPULATION_CLASS_ALIASES.get(population_class.lower(), population_class)

            estimate_method = normalized.get("estimate_method")
            if isinstance(estimate_method, str) and estimate_method not in _VALID_ESTIMATE_METHODS:
                normalized["estimate_method"] = "source_direct"

        # Some GPT Pro bundles emit empty-string quality tiers for incomplete episodes.
        # Normalize to null so optional quality_tier fields remain contract-valid.
        if filename in {"episodes.json", "estimates.json"}:
            quality_tier = normalized.get("quality_tier")
            if quality_tier == "":
                normalized["quality_tier"] = None
            elif isinstance(quality_tier, str):
                normalized["quality_tier"] = _QUALITY_TIER_ALIASES.get(quality_tier.lower(), quality_tier)

        if filename == "episodes.json" and normalized.get("end_date") == "":
            normalized["end_date"] = None

        if filename == "assumptions.json":
            category = normalized.get("category")
            if isinstance(category, str):
                normalized_category = _ASSUMPTION_CATEGORY_ALIASES.get(category.lower(), category.lower())
                if normalized_category not in {"geometry", "displacement", "troop_strength", "casualty_status", "time_interpolation", "other"}:
                    normalized_category = "other"
                normalized["category"] = normalized_category

            sensitivity = normalized.get("sensitivity")
            if isinstance(sensitivity, str):
                lowered = sensitivity.lower().strip().rstrip(".")
                if lowered in {"low", "medium", "high"}:
                    normalized["sensitivity"] = lowered
                elif "high" in lowered and "medium" in lowered:
                    normalized["sensitivity"] = "high"
                elif "high" in lowered:
                    normalized["sensitivity"] = "high"
                elif "medium" in lowered:
                    normalized["sensitivity"] = "medium"
                elif "low" in lowered:
                    normalized["sensitivity"] = "low"

        if filename == "estimates.json":
            estimate_method = normalized.get("estimate_method")
            if isinstance(estimate_method, str) and estimate_method not in _VALID_ESTIMATE_METHODS:
                normalized["estimate_method"] = "derived_from_sources"

            unknown_status_rule = normalized.get("unknown_status_rule")
            metric_name = normalized.get("metric_name")
            if metric_name == "dr_v1_direct" and unknown_status_rule in {None, "", "not_applicable"}:
                normalized["unknown_status_rule"] = "strict"
            elif isinstance(unknown_status_rule, str) and unknown_status_rule not in _VALID_UNKNOWN_STATUS_RULES:
                lowered = unknown_status_rule.lower()
                if "not applicable" in lowered:
                    normalized["unknown_status_rule"] = "not_applicable"
                elif "case" in lowered and "specific" in lowered:
                    normalized["unknown_status_rule"] = "case_specific"
                else:
                    normalized["unknown_status_rule"] = "strict"

        if filename == "estimates.json" and _should_drop_null_placeholder_estimate(normalized):
            continue

        cleaned.append(normalized)
    return cleaned


def _should_drop_null_placeholder_estimate(item: dict[str, Any]) -> bool:
    null_values = (
        item.get("value_low") is None
        and item.get("value_best") is None
        and item.get("value_high") is None
    )
    if not null_values:
        return False

    metric_name = item.get("metric_name")
    if metric_name in {"dr_v1_direct", "dr_midpoint_fallback"}:
        return True

    input_claim_ids = item.get("input_claim_ids")
    if input_claim_ids == []:
        return True

    return False


def _drop_non_publishable_dr_estimates(payloads: dict[str, dict[str, Any] | list[dict[str, Any]]]) -> None:
    episodes = payloads.get("episodes.json")
    estimates = payloads.get("estimates.json")
    if not isinstance(episodes, list) or not isinstance(estimates, list):
        return

    full_by_episode = {
        item.get("episode_id"): bool(item.get("full_estimate_completed"))
        for item in episodes
        if isinstance(item, dict) and item.get("episode_id")
    }
    if not full_by_episode:
        return

    filtered: list[dict[str, Any]] = []
    for item in estimates:
        if not isinstance(item, dict):
            filtered.append(item)
            continue
        metric_name = item.get("metric_name")
        episode_id = item.get("episode_id")
        if metric_name in {"dr_v1_direct", "dr_midpoint_fallback"} and not full_by_episode.get(episode_id, False):
            continue
        filtered.append(item)
    payloads["estimates.json"] = filtered


def _reconcile_episode_completion_flags(payloads: dict[str, dict[str, Any] | list[dict[str, Any]]]) -> None:
    episodes = payloads.get("episodes.json")
    estimates = payloads.get("estimates.json")
    if not isinstance(episodes, list) or not isinstance(estimates, list):
        return

    publishable_by_episode: dict[str, bool] = {}
    for item in estimates:
        if not isinstance(item, dict):
            continue
        episode_id = item.get("episode_id")
        metric_name = item.get("metric_name")
        if not isinstance(episode_id, str) or metric_name not in {"dr_v1_direct", "dr_midpoint_fallback"}:
            continue
        if item.get("value_low") is not None or item.get("value_best") is not None or item.get("value_high") is not None:
            publishable_by_episode[episode_id] = True

    for item in episodes:
        if not isinstance(item, dict):
            continue
        episode_id = item.get("episode_id")
        if not isinstance(episode_id, str):
            continue
        if item.get("full_estimate_completed") and not publishable_by_episode.get(episode_id):
            item["full_estimate_completed"] = False


def _derive_slug_from_filename(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"^overkill_", "", stem)
    stem = re.sub(r"_research_bundle(?: \(\d+\))?$", "", stem)
    return stem
