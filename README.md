# Overkill <img src="logo/jellyfish.png" alt="" width="48" align="right">

**[Explore the live site](https://smkwray.github.io/overkill/)**

Overkill is a static research explorer for relative risk (RR) in armed conflict: the ratio of the military direct-death rate to the civilian direct-death rate, per person-month of exposure, within a bounded conflict episode. An RR above 1 means military personnel died at a higher per-person rate than civilians; below 1, civilians faced the higher rate.

This repository contains the research-bundle schema and validator, the tools that import, audit, and export bundles, and the static explorer. The research bundles themselves are not included; the tools read them from `research/input/gptpro/`. The explorer's data is committed as `static/data/index/bundles.json`: 90 conflicts from 1915 to the present, split into 282 episodes, 56 of them with an RR estimate, citing 556 sources.

## Why relative risk

Raw casualty ratios ("X soldiers died for every civilian") can invert the real risk when civilians flee and the populations present differ in size. At Stalingrad, about 440,000 military and 50,000 civilian deaths give a raw ratio of roughly nine soldiers per civilian. But most civilians had evacuated: about 650,000 civilian person-months of exposure remained against 6.8 million military person-months. A civilian trapped in the city faced a monthly death rate of about 7.7%, against about 6.5% for a soldier, so RR = 0.84. Relative risk asks, for each person actually present, who was more likely to die.

```
RR = (military direct deaths / military person-months) / (civilian direct deaths / civilian person-months)
```

Person-months are the number of people present in the conflict theater multiplied by the time they were there, adjusted for evacuation, displacement, mobilization, and reinforcement. Every estimate has low, best, and high bounds. Where one side has zero deaths, the estimate is marked as censored instead of given a point value.

Each episode also has a quality tier:

| Tier | Evidence level |
|---|---|
| A | Strong source triangulation; denominators closely tied to the theater; moderate uncertainty |
| B | Good evidence, with some denominator or status ambiguity |
| C | Sparse or conflicting evidence; an estimate is possible but with wide bounds |
| D | Mostly model-generated or highly uncertain |

## How the research bundles are made

The research bundles were generated with OpenAI GPT Pro (GPT-5.2 Pro and GPT-5.4 Pro) in the ChatGPT web interface, with web search, from a fixed research prompt. For each conflict, the prompt has the model split the conflict into episodes wherever the theater, belligerents, or mode of violence changes; find and compare sources, preferring named-victim registries, incident databases, truth commissions, and scholarly reconstructions over official, NGO, press, and model-based figures; and cite each claim with author, title, year, and page or section. Military, civilian, and unknown-status deaths are kept separate, unknown-status deaths are never silently assigned to either side, indirect deaths are kept out of the baseline measure, and model-based figures are labeled. Each episode records its assumptions, open questions, and a quality tier, and may include auxiliary counts of women and children killed and of which side inflicted the deaths. The model returns structured JSON, which the tools in this repository import and check against the bundle schema.

## Limitations

- GPT Pro's web search may favor sources that are digitized, in English, and widely indexed, so regional-language scholarship and paywalled archives may be underrepresented.
- Some conflicts have deep literatures and others almost none; quality tiers reflect this, but gaps are hard to see from outside.
- Where a figure is disputed, a bundle may give the mainstream view without representing every position.
- Classifying police, paramilitaries, and civil-defense units as military or civilian is a judgment call. Status rules (for example, police count as military only when deployed as combat forces) and alternative scenarios are recorded, but other reasonable rules give different numbers.
- RR depends on where an episode's boundaries in space and time are drawn. Short episodes, and events that combine distinct phases such as an assault followed by massacres, are especially sensitive.
- An LLM can misattribute a figure or misread a source's scope. Automated validation checks structure and cross-references, not the accuracy of each citation.

## Contributing

To report a factual error, suggest a missing source, flag a contested claim, or request a new episode, open a [GitHub issue](https://github.com/smkwray/overkill/issues/new/choose) with the matching template. Include specific references (author, title, year, pages) where you can.

## Using the tools

Requires Python 3.14 or later.

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

overkill ingest-markdown-bundles path/to/markdown/    # import GPT Pro markdown output into research/input/gptpro/
overkill validate-bundle research/input/gptpro/<bundle>
overkill audit-bundles                                # status audit in research/derived/bundle_audit.json
overkill export-demo-data                             # explorer data in static/data/index/
overkill export-best-supported-episodes
overkill serve-demo                                   # local explorer at http://127.0.0.1:8765
pytest
```

The importer skips bundles that already exist and removes duplicate conflict IDs; pass `--overwrite` to replace existing bundles. `export-demo-data` keeps only the fields the explorer shows. The tests use a synthetic bundle in `tests/fixtures/bundles/`.

## License

MIT. See [LICENSE](LICENSE).
