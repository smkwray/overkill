# Overkill <img src="logo/jellyfish.png" alt="" width="48" align="right">

**[Explore the live site](https://smkwray.github.io/overkill/)**

Overkill is a static research explorer for **relative risk** estimates in armed conflict — the exposure-adjusted ratio of military to civilian direct-death rates within a defined conflict episode.

## What is relative risk?

Relative risk compares the rate at which two groups experience an outcome, after adjusting for how many people in each group were actually exposed. In its general form:

```
            (events in group A / population of group A exposed)
    RR  =  ——————————————————————————————————————————————————————
            (events in group B / population of group B exposed)
```

An RR of 1 means both groups face the same rate. Above 1, group A's rate is higher; below 1, group B's rate is higher.

This is not a novel statistic. Relative risk is foundational in epidemiology and is used routinely in clinical trials, occupational health, and environmental science — anywhere raw event counts would be misleading because the groups differ in size or exposure time.

Overkill applies the same logic to armed conflict. The two groups are **military/combatant personnel** and **civilians**. The outcome is **direct conflict death**. The exposure denominator is **person-months** — the number of people physically present in the conflict theater, multiplied by the time they were there. When an RR is above 1, military personnel face a higher per-person death rate than civilians. When it is below 1, civilians face the higher rate. The raw body count may tell a completely different story, because the two populations are almost never the same size and often change dramatically over the course of an episode through evacuation, displacement, mobilization, and reinforcement.

## Why relative risk, not casualty counts?

Simple casualty ratios — "X soldiers died for every Y civilians" — are the standard shorthand for how discriminate a conflict was. They are also misleading. A low civilian count can mean civilians were protected, or it can mean most civilians fled and the ones who stayed faced terrible odds. Simple ratios cannot distinguish between these cases; relative risk can.

**Stalingrad illustrates the problem.** The simple ratio is 0.11 — roughly 50,000 civilian deaths vs 440,000 military. By raw body count, this looks like one of history's most favorable episodes for civilian protection: nine soldiers for every civilian. But adjust for the populations actually present and the picture inverts. Most of Stalingrad's civilians had evacuated; only about 650,000 civilian-person-months of exposure remained, against 6.8 million military. An individual civilian trapped in the city faced a ~7.7% monthly death rate versus ~6.5% for a soldier. The relative risk is 0.84 — civilians were dying at a *higher* rate than combatants. The simple ratio rewards evacuation for shrinking the denominator without asking whether the people who could not leave were protected. Relative risk asks the question that matters: **for each person actually present, who faced greater risk of dying?**

## Reading the estimates

| Value | Meaning |
|-------|---------|
| RR > 1 | Military personnel face a higher per-person direct-death rate than civilians |
| RR = 1 | Equal rates — what you would expect if violence fell indiscriminately on everyone present, regardless of status |
| RR < 1 | Civilians face a higher per-person direct-death rate than military personnel |

Every episode also carries a **quality tier**:

| Tier | Evidence level |
|------|----------------|
| A | Strong source triangulation; denominators closely tied to theater; moderate uncertainty |
| B | Good evidence but some denominator or status ambiguity |
| C | Sparse or conflicting evidence; estimate possible but wide uncertainty bands |
| D | Mostly model-generated or highly uncertain |

All estimates include low/best/high bounds. Where one side has zero deaths, the estimate is flagged as censored rather than assigned a false point value.

## Coverage

The dataset currently spans conflicts from 1915 to the present, covering episodes across the Middle East, Europe, Asia, Africa, and Latin America. Research bundles are organized by conflict family, with each family split into bounded episodes wherever the theater, belligerent structure, or violence mode changes materially.

Coverage is actively expanding. See **Contributing** below to suggest episodes not yet included.

## Research methodology

The research bundles in this project were generated using **OpenAI GPT Pro** (GPT-5.2 Pro and GPT-5.4 Pro) with extended thinking, via the ChatGPT web interface. GPT Pro has access to web search and retrieves real, citable sources — every claim in every bundle is tied to a specific source with author, title, year, and page or section reference. This is not generation from training data alone; the model actively searches for and cites published scholarship, reports, and databases.

Each conflict episode was produced from a detailed, self-contained prompt template. The prompt defines the full research workflow the model must follow:

1. **Episode splitting.** The model first proposes how to divide a conflict into episodes — bounded by theater, belligerent structure, and violence mode — rather than forcing a single whole-war estimate.
2. **Source identification.** The model searches for and compares sources across a preference hierarchy: named-victim registries, incident databases, truth commissions, scholarly reconstructions, official records, NGO/UN reporting, journalism, and model-based estimates (last resort). For each source it records what the source actually counts, what it excludes, its date and geographic scope, and a key excerpt or quotation.
3. **Numerator and denominator extraction.** Military deaths, civilian deaths, and unknown-status deaths are kept strictly separate. Population-exposure denominators use subnational theater-level populations adjusted for displacement, not whole-country figures. The preferred denominator is person-months; midpoint approximations are flagged as fallbacks.
4. **Subgroup metrics.** Where sources support it, the model extracts women and children death counts (preferring under-15 as the strongest proxy for non-combatants) as auxiliary series. These are recorded alongside the main estimates but are not used in the relative risk calculation itself.
5. **Side attribution.** Where sources support it, the model records both which population was killed and which force inflicted the deaths — victim class and perpetrator identity are tracked independently.
6. **Uncertainty and assumptions.** Every estimate carries low/best/high bounds. An explicit assumptions register documents theater footprint choices, displacement timing, troop-strength ranges, unknown-status handling, and source disagreements. Each episode receives a quality tier (A through D) with justification.
7. **Machine-readable output.** The model returns structured JSON blocks for conflict metadata, episodes, sources, claims, estimates, assumptions, and open questions — ready for automated ingestion and validation.

The prompts enforce strict rules: deaths and casualties are never conflated, indirect deaths are never mixed into the baseline metric, unknown-status cases are never silently assigned to civilians or military, and model-generated estimates are always labelled as such.

The prompt template used to generate research bundles is available at [`prompt-template.md`](prompt-template.md). It can be copied directly into GPT Pro to reproduce existing bundles or research new conflict episodes.

### Known limitations

- **Source selection bias.** Although GPT Pro searches the web and cites real sources, its search behavior may favor sources that are digitized, English-language, and widely indexed. Regional-language scholarship, paywalled archives, and recently released datasets may be underrepresented.
- **Source availability.** Some conflicts have deep, well-documented literatures; others have almost none. The quality tier assigned to each episode reflects this, but coverage gaps are difficult to detect from the outside.
- **Contested sources.** Some source claims are disputed among scholars or between parties to a conflict. GPT Pro may present a mainstream view that does not fully represent every position in an active debate.
- **Classification judgments.** Calculating relative risk requires deciding who counts as military and who counts as civilian. Cases like police forces, paramilitaries, and civil defense units can reasonably be classified either way depending on context. Where status is ambiguous, the project uses explicit rules (e.g. police count as military only when deployed as combat forces) and runs multiple scenarios rather than forcing a single assignment. These choices affect the final estimates, and different reasonable rules would produce different numbers.
- **Episode boundary sensitivity.** RR depends on how the episode is defined in space and time. An event that combines distinct phases — such as a military assault on border positions followed by massacres in civilian towns — can produce a misleading aggregate if treated as a single episode, because the two phases had different targeting patterns and different exposed populations. Short-duration episodes are especially sensitive: small changes in the assumed theater or time window can shift the denominators substantially. The project splits episodes where the dynamics clearly change, but not every boundary choice is unambiguous.
- **Model limitations.** While every claim is sourced, LLM outputs can occasionally misattribute a figure or misinterpret a source's scope. Every bundle undergoes automated validation, but human review remains valuable — especially for politically sensitive episodes.

This project is designed to be improved iteratively. If you find an error, a missing source, or a contested claim that deserves better representation, see **Contributing** below.

## Contributing

The best way to suggest corrections, flag missing sources, or propose new conflict episodes is to **open a GitHub Issue** on this repository. To help us act on your suggestion quickly, please use one of the issue templates:

- **Data correction** — for factual errors, misattributed figures, or incorrect source citations in an existing bundle.
- **Missing source** — for published research, databases, or reports that should inform an episode's estimates.
- **Contested claim** — for cases where the current bundle does not adequately represent a significant scholarly or evidentiary disagreement.
- **New episode request** — for conflict episodes not yet covered.

When filing an issue, please include specific references (author, title, year, pages) where possible. Vague objections are hard to act on; a citation is worth a thousand words.

We do not accept corrections via email. Public issues keep the audit trail visible and let others benefit from the same discussion.

## Development

The sections below are for contributors working on the codebase.

### Python quickstart

```bash
set -a; source .env; set +a
"$PROJECT_VENV_ROOT/bin/python" -m pip install -r requirements.txt
"$PROJECT_VENV_ROOT/bin/python" -m overkill.cli validate-bundle research/input/gptpro/bosnian-war
"$PROJECT_VENV_ROOT/bin/python" -B -m pytest
```

### Ingest markdown bundles

Use the importer when you have new GPT Pro markdown outputs in Downloads (or any folder).
Defaults are safe for repeat runs: same-`conflict_id` duplicates are de-duplicated, existing bundle directories are skipped, and imported bundles are normalized to the repo contract before validation.

```bash
set -a; source .env; set +a
"$PROJECT_VENV_ROOT/bin/python" -m overkill.cli ingest-markdown-bundles /path/to/folder/with/markdowns
```

File + directory mixes are supported:

```bash
set -a; source .env; set +a
"$PROJECT_VENV_ROOT/bin/python" -m overkill.cli ingest-markdown-bundles \
  /path/to/folder \
  /path/to/one/specific_bundle.md
```

Useful flags:
- `--json`: machine-readable ingest summary
- `--overwrite`: replace existing bundle directories (off by default)
- `--skip-validation`: skip post-import validation (not recommended)
- `--pattern`: customize directory glob (default `overkill_*_research_bundle*.md`)

### Bundle audit

To write the current taxonomy/provisional-status audit and relationship-aware report:

```bash
set -a; source .env; set +a
"$PROJECT_VENV_ROOT/bin/python" -m overkill.cli audit-bundles
```

This writes:
- `research/derived/bundle_relationships.json`: machine-readable parent/child, superseding, umbrella, and provisional-bundle metadata
- `research/derived/bundle_audit.json`: generated audit report over the current bundle set

To export only the strongest currently publishable episodes:

```bash
set -a; source .env; set +a
"$PROJECT_VENV_ROOT/bin/python" -m overkill.cli export-best-supported-episodes
```
