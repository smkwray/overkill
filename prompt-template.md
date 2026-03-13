# GPT Pro Research Prompt Template

Copy this entire prompt into GPT Pro (GPT-5.2 Pro or GPT-5.4 Pro with extended thinking). Replace the placeholder values in the **Conflict to research** section with your target. This file is standalone and includes the full methodology, classification rules, and output schema required by the Overkill ingestion pipeline.

---

You are a **conflict research analyst and data packager**. Your task is to produce a research bundle for estimating a conflict episode's **Relative Risk (RR)** — the exposure-adjusted ratio of military to civilian direct-death rates.

## Mission

Research the conflict below and return a source-grounded, uncertainty-aware package that can be ingested by the Overkill validation and visualization pipeline.

### Conflict to research
- Conflict family or war: `REPLACE_WITH_CONFLICT_NAME`
- Optional focus/theater/phase: `REPLACE_OR_DELETE`
- Optional date range constraint: `YYYY-MM-DD` to `YYYY-MM-DD`
- Optional notes: `REPLACE_OR_DELETE`

## Episode anchors to prioritize
- Propose defensible episodeization first, then prioritize episodes with strongest source coverage.

## Non-negotiable project rules

1. **Do not use whole-country civilian populations for subnational conflicts.**
2. **Do not use whole-country military populations unless the whole force was genuinely deployed to the episode.**
3. Prefer **person-month exposure denominators** over simple midpoint populations.
4. The baseline metric is **direct violent deaths only**. Indirect deaths are separate.
5. Keep **civilian**, **military/combatant/organized armed personnel**, and **unknown status** separate.
6. Every important numeric claim must be tied to a source with page/section/URL and a short excerpt or quotation.
7. When sources conflict, do not average mechanically. Explain why they differ.
8. If good figures do not exist, you may create model-based estimates **only after exhausting better sources**, and you must label them clearly as model-generated.
9. If the conflict is large or heterogeneous, split it into **episodes** rather than forcing a single whole-war estimate.
10. Be conservative about confidence. Wide intervals are better than false precision.

## Mortality-classification rules (non-negotiable)

- Preferred child subgroup metric: `children_u15` as the strongest proxy for not-plausibly-combatants.
- If `u15` is unavailable, capture source-native thresholds exactly (for example `u18`); do not silently harmonize.
- Retrieve subgroup metrics when available:
  - `civ_deaths_children_u15_direct`
  - `civ_deaths_children_u18_direct`
  - `civ_deaths_women_direct`
- Keep subgroup metrics auxiliary; do not replace core civilian/military/unknown estimates with subgroup series.
- Always distinguish deaths from casualties. Casualties may include injuries.
- Never ingest casualties as deaths unless the source explicitly defines casualties as fatalities only.
- Retrieve casualty series when useful and keep them separate:
  - `civ_casualties_direct`
  - `mil_casualties_direct`
  - `unknown_casualties_direct`
  - optional injuries if separable
- If any deaths figure is derived from a broader casualty source, include an explicit derivation note tied to source wording.
- Do not infer indirect deaths by subtraction unless the source itself explicitly defines the residual as indirect/nonviolent/deprivation mortality.
- If a source gives totals (total deaths, war deaths, conflict deaths, casualties, excess deaths) without a clean direct/indirect split, classify as `mixed_mortality` or `unclassified_mortality_context`.
- Base RR uses only explicit direct violent deaths.
- Indirect deaths are auxiliary and only populated when source wording explicitly supports indirect classification.
- Always quote exact source wording when there is ambiguity around deaths vs casualties or direct vs indirect.

## Side-attribution rules (non-negotiable)

- Distinguish victim class from inflicting side. `population_class` tells us who the victims were, not who inflicted the deaths.
- Whenever the source supports it, record both:
  - `victim_side`
  - `inflicting_side`
- If the source supports victim class but not attacker identity, leave side fields null rather than infer.
- If the source supports attacker identity but only at a coalition/category level, use that exact level rather than over-specifying.
- If the same episode has multiple side-specific death series, keep them as separate claim/estimate rows rather than collapsing them into one blended row.
- Always note attribution ambiguity in `transform_note`, `confidence_note`, or `uncertainty_note` when side assignment is contested or only partly explicit.

## Operational definitions to use

### 1) Core metric

Preferred metric:

```
RR = (military direct deaths / military person-months) / (civilian direct deaths / civilian person-months)
```

Fallback if person-months are impossible:
- midpoint approximation using average exposed populations
- must be clearly flagged as approximate

### 2) Civilian
A person who is not an active member of an organized armed force or armed group during the relevant period.

### 3) Military / combatant / organized armed personnel
Use this umbrella operational category for:
- regular armed forces
- mobilized reservists once operationally active
- rebel/insurgent fighters
- militias/paramilitaries functioning as combat forces
- police/gendarmerie/internal troops when used as combat forces
- foreign fighters attached to organized armed entities
- private military contractors in armed operational roles

### 4) Direct conflict death
Deaths from the immediate violent effects of conflict:
- shelling, bombing, drone/missile strike, gunfire
- massacre, execution, torture resulting in death
- violent detention deaths attributable to conflict actors
- direct-attack deaths during forced displacement

### 5) Indirect death
Deaths from deprivation, famine, disease, exposure, healthcare collapse, etc.
- store separately
- do not include in the baseline RR

### 6) Theater / exposed population
Count only people in the actual area of conflict for the episode.
- If fighting is limited to a province, city, district, corridor, enclave, or moving front, use that.
- If civilians flee the area, reduce the civilian denominator accordingly.
- If air/naval/offshore/adjacent units are directly operating against the theater, they may be counted in the military denominator even if they are just outside the civilian impact polygon.

### 7) Unknown status
Keep unknown-status deaths separate unless you explicitly run a sensitivity allocation.

## Required research workflow

### Step A - define the conflict family and candidate episodes
Before estimating anything, determine whether the conflict should be split into multiple episodes.

Split when:
- the theater changes materially
- the belligerent structure changes materially
- violence mode changes materially
- available sources align with different geographies or periods
- a whole-war denominator would obviously be misleading

Return a proposed episode list first, even if the final answer later covers only a subset in full detail.

### Step B - map the geography
For each episode:
- describe the theater in plain language
- state whether it is national, subnational, city-level, corridor-level, cross-border, or mixed
- name the relevant provinces/governorates/districts/cities if possible
- note whether the geometry likely changed over time
- explain why this is the right denominator footprint

### Step C - identify numerator sources
Find and compare sources for:
- military/combatant direct deaths
- civilian direct deaths
- unknown-status direct deaths
- side attribution for who inflicted those deaths
- subgroup direct-death metrics (children/women where available)
- casualty/injury metrics as auxiliary series
- optionally indirect deaths in a separate section

For each source:
- state what it actually counts
- classify it as one of: direct deaths / indirect deaths / injuries / total casualties / excess deaths / mixed mortality / unclassified mortality context
- state what it excludes
- state the date range and geography
- note whether it is event-based, named-victim, official, journalistic, scholarly, legal, NGO, UN, or model-based
- extract the usable numeric claim(s)
- state whether the source identifies the inflicting side, the victim side, both, or neither
- for subgroup/casualty metrics, include: exact wording, age/sex rule, whether deaths/injuries/total casualties, and whether status is explicit or inferred
- if converting any casualty term into a deaths claim, include explicit source-grounded derivation logic; otherwise keep deaths null

### Step D - identify denominator sources
Find and compare sources for:
- civilian populations in the episode theater
- displacement/outflow/return
- troop deployments or force presence in the episode theater
- force rotations or mobilization that affect exposure time

### Step E - derive low / best / high estimates
For each episode, derive:

1. `mil_deaths_direct`
2. `civ_deaths_direct`
3. `unknown_deaths_direct`
4. `mil_person_months`
5. `civ_person_months`
6. `dr_v1_direct`
7. auxiliary subgroup/casualty metrics when available

Each should have:
- low
- best or median
- high
- method label: `source_direct` / `derived_from_sources` / `model_generated`

### Step F - document assumptions and uncertainty
Create an explicit assumptions register covering:
- theater footprint choices
- displacement timing
- troop deployment ranges
- unknown-status handling
- missing months
- source disagreement
- fallback midpoint approximations, if used

### Step G - rate the episode
Assign each episode a quality tier:
- `A` strong triangulation
- `B` good but imperfect
- `C` sparse/conflicting
- `D` mostly model-based / highly uncertain

Explain the rating.

## Source behavior rules

### Prioritize high-quality source types
Prefer, when available:
1. named-victim registries / microdata
2. conflict-specific incident databases
3. truth commissions / legal findings / major scholarly reconstructions
4. official records used critically
5. reputable NGO / UN reporting
6. high-quality journalism with transparent sourcing
7. model-based estimates

### Do not flatten source differences
If two sources disagree, explain that explicitly.

### Quote key evidence
For major numeric claims, give a short quotation or paraphrase with page/section/URL so the claim can be audited later.

## Required output structure

Your response must contain the following sections in this order.

## Downloadable file requirement
- Primary deliverable: provide a downloadable Markdown file named `overkill_CONFLICT-ID-HERE_research_bundle.md` containing sections 1-9 and all required JSON blocks.
- If your interface cannot attach files, output the complete file contents in one fenced `markdown` block and prepend: `FILE_NAME: overkill_CONFLICT-ID-HERE_research_bundle.md`.

# 1. Executive summary
Briefly state:
- what conflict/family you researched
- whether you split it into episodes
- which episode(s) are fully estimated in this answer
- the main takeaways and biggest uncertainty drivers

# 2. Definitions check
In 5-10 bullets, confirm how you operationalized:
- civilian
- military/combatant
- direct death
- indirect death
- theater
- displacement
- unknown status
- preferred RR formula

# 3. Conflict-family overview
Provide:
- one-paragraph overview
- countries/territories involved
- date span
- why episode splitting is necessary or unnecessary

# 4. Proposed episodes
Return a table with:
- `episode_id`
- `episode_name`
- `start_date`
- `end_date`
- `geographic_scope`
- `why_split`
- `full_estimate_completed` (yes/no)

# 5. Source review
For each important source, provide:
- what it measures
- usable claims
- strengths
- limitations
- whether it is suitable for numerator, denominator, or both

# 6. Episode-by-episode research notes
For each episode fully estimated in this answer, include:
- theater description
- numerator sources
- denominator sources
- derivation notes
- low/best/high estimates
- main caveats
- quality tier

# 7. Assumptions register
List every material assumption.

# 8. Open problems
List what remains uncertain or missing.

# 9. Machine-readable bundle
Return the exact JSON blocks below.

## Required JSON block 1 - `conflict.json`
```json
{
  "conflict_id": "",
  "conflict_name": "",
  "aliases": [],
  "family_summary": "",
  "start_date": "",
  "end_date": "",
  "countries": [],
  "regions": [],
  "notes": ""
}
```

## Required JSON block 2 - `episodes.json`
```json
[
  {
    "episode_id": "",
    "conflict_id": "",
    "episode_name": "",
    "start_date": "",
    "end_date": "",
    "time_unit": "month",
    "geographic_scope": "",
    "countries": [],
    "admin_units": [],
    "theater_description": "",
    "geometry_method_note": "",
    "military_area_note": "",
    "civilian_area_note": "",
    "split_reason": "",
    "full_estimate_completed": true,
    "quality_tier": "",
    "quality_note": ""
  }
]
```

## Required JSON block 3 - `sources.json`
```json
[
  {
    "source_id": "",
    "citation_short": "",
    "title": "",
    "author_or_org": "",
    "year": "",
    "source_type": "",
    "url": "",
    "pages_or_sections": "",
    "geographic_scope": "",
    "date_scope": "",
    "variables_supported": [],
    "strengths": "",
    "limitations": "",
    "notes": ""
  }
]
```

## Required JSON block 4 - `claims.json`
```json
[
  {
    "claim_id": "",
    "episode_id": "",
    "source_id": "",
    "variable_name": "",
    "population_class": "military|civilian|unknown",
    "victim_side": null,
    "inflicting_side": null,
    "death_type": "direct|indirect|not_applicable",
    "start_date": "",
    "end_date": "",
    "geographic_scope": "",
    "value_low": null,
    "value_best": null,
    "value_high": null,
    "unit": "",
    "estimate_method": "source_direct|derived_from_sources|model_generated",
    "excerpt": "",
    "pages_or_sections": "",
    "transform_note": "",
    "confidence_note": ""
  }
]
```

## Required JSON block 5 - `estimates.json`
```json
[
  {
    "estimate_id": "",
    "episode_id": "",
    "metric_name": "mil_deaths_direct|civ_deaths_direct|unknown_deaths_direct|mil_person_months|civ_person_months|dr_v1_direct|dr_midpoint_fallback",
    "victim_side": null,
    "inflicting_side": null,
    "value_low": null,
    "value_best": null,
    "value_high": null,
    "unit": "",
    "estimate_method": "source_direct|derived_from_sources|model_generated",
    "input_claim_ids": [],
    "formula_note": "",
    "uncertainty_note": "",
    "unknown_status_rule": "strict|proportional|case_specific|not_applicable",
    "quality_tier": "",
    "quality_note": ""
  }
]
```

## Required JSON block 6 - `assumptions.json`
```json
[
  {
    "assumption_id": "",
    "episode_id": "",
    "category": "geometry|displacement|troop_strength|casualty_status|time_interpolation|other",
    "assumption_text": "",
    "rationale": "",
    "sensitivity": "low|medium|high"
  }
]
```

## Required JSON block 7 - `open_questions.json`
```json
[
  {
    "episode_id": "",
    "question": "",
    "why_it_matters": "",
    "what_would_resolve_it": ""
  }
]
```

## JSON formatting rules
- Use valid JSON.
- Use ISO dates where possible: `YYYY-MM-DD`.
- If only month known, use first day of month and explain in notes.
- If only year known, use `YYYY-01-01` and explain in notes.
- Use `null` rather than empty strings for unknown numeric values.
- Keep arrays valid.
- `episode_id` values must be null or reference a valid `episode_id` from `episodes.json`.

## Calculation rules for the final RR estimate

### Preferred
If you can estimate person-month denominators:
- compute `dr_v1_direct`

### Fallback
If you cannot estimate person-month denominators but can estimate exposed midpoint populations:
- compute `dr_midpoint_fallback`
- explain why person-months were not feasible

### Zero-death rule
If one side has zero direct deaths:
- do not fake a point estimate using arbitrary continuity corrections
- instead say the estimate is censored toward zero or infinity
- in JSON, you may leave point values null and explain in `uncertainty_note`

## Final self-audit checklist

Before you finish, verify that:
- no subnational episode uses a whole-country denominator without explicit justification
- every published estimate points back to claim ids
- unknown-status cases are not silently folded into civilians or military
- direct and indirect deaths are kept separate
- source disagreement is explained
- model-generated estimates are labelled
- at least one explicit uncertainty note appears for each episode
- the machine-readable bundle is internally consistent

Now perform the research and return the full package.
