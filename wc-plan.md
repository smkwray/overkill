# Women & Children Relative Risk — Research Plan

## Goal

Compute a demographic discrimination ratio for women and children within the civilian population, analogous to DR but answering: **were women/children dying at higher rates than adult male civilians?**

Formula:
```
WC_DR = (adult_male_civ_death_rate) / (women_children_death_rate)
```
- WC_DR > 1 → adult men at higher risk (e.g. military-age males targeted)
- WC_DR < 1 → women/children at higher risk (indiscriminate or deliberately targeting vulnerable)
- WC_DR ≈ 1 → proportional to population share

---

## What We Have

### Numerators (death counts — partial)

| Metric | Episodes | Notes |
|--------|----------|-------|
| `civ_deaths_women_direct` | ~9 bundles | Mostly from B'Tselem, CNMH, SNHR, OCHA |
| `civ_deaths_children_u18_direct` | ~12 bundles | Most common child metric |
| `civ_deaths_children_u15_direct` | ~3 bundles | Different age cutoff |
| `civ_deaths_children_direct_unspecified_age_cutoff` | ~2 bundles | Source doesn't specify age |
| `civ_deaths_direct` (total) | All 55 DR episodes | Needed to derive adult male deaths as residual |

**Derivation possible where both women + children exist:**
```
adult_male_civ_deaths = civ_deaths_direct − civ_deaths_women − civ_deaths_children
```

**Episodes with BOTH women AND children counts (best candidates):**
1. Bojaya church strike (79 civ: 41 women, 48 children)
2. Cast Lead main phase (773 civ: 107 women, 320 children)
3. Samashki operation (140 civ: 13 women, 7 children)
4. Kunduz city fall (289 civ: 43 women, 10 children)
5. Great March of Return (142 civ: 1 woman, 35 children)
6. Iran bombardment of Israel 2025 (27 civ: 17 women, 4 children)
7. Linebacker II Hanoi (1,323 civ: 91 women, 55 children)

### Denominators (person-months — MISSING)

**We have none of these:**
- `civ_person_months_women` — women present in theater over time
- `civ_person_months_children_u18` — children present in theater over time
- `civ_person_months_adult_male` — adult male civilians present over time

We only have aggregate `civ_person_months` (total civilian exposure).

---

## What GPT-Pro Needs to Research

### Priority 1: Demographic baselines for existing episodes

For each of the 7 episodes with both women + children death counts, find the **pre-conflict demographic breakdown** of the affected civilian population:

| Episode | What to find | Likely sources |
|---------|-------------|----------------|
| **Bojaya 2002** | Sex/age breakdown of Bellavista/Bojayá municipality | Colombia 2005 census (DANE), CNMH report demographics |
| **Cast Lead 2008-09** | Gaza Strip sex/age pyramid, Dec 2008 | PCBS mid-2008 population estimates (they publish age-sex tables) |
| **Samashki 1995** | Samashki village demographics pre-attack | Russian 1989 census for Achkhoy-Martan district; estimates of Chechen rural demographics |
| **Kunduz 2015** | Kunduz city age-sex distribution | Afghanistan CSO 2014-15 estimates; UNFPA Afghanistan |
| **Great March of Return 2018** | Gaza border-zone protest demographics | OCHA humanitarian profiles; PCBS; protest attendance reports |
| **Iran strikes on Israel 2025** | Beit Shemesh / affected area demographics | Israel CBS (Central Bureau of Statistics) city-level data |
| **Linebacker II 1972** | Hanoi civilian population demographics, Dec 1972 | Vietnam GSO historical data; wartime census estimates; UN Demographic Yearbook 1972 |

**What to record per episode:**
- Total civilian population in theater (should match existing `civ_person_months` basis)
- % female (all ages)
- % under 18 (or under 15, matching the death count age cutoff)
- % adult male (derived: 100% − female% − children%)
- Source citation and confidence level
- Whether displacement was sex/age-differential (did women/children flee more or less than men?)

### Priority 2: Demographic baselines for episodes with children-only data

These episodes have children death counts but no women data. Still useful for a children-specific risk ratio:

| Episode | Children data | Baseline needed |
|---------|--------------|-----------------|
| Gaza 2014 (Protective Edge) | 526 u18 | PCBS mid-2014 |
| Eastern Ghouta 2018 | 179 u18 | Pre-siege Ghouta population estimates (OCHA, SNHR) |
| October 7 attack | 39 u18 | Israel CBS for Be'eri / Sderot / kibbutz communities |
| Sri Lanka NFZ 2009 | 200 u15 | Sri Lanka DCS for Mullaitivu district |
| Gaza 2023-present (subgroup data) | Multiple episodes | PCBS mid-2023 |

### Priority 3: Women/children death counts for HIGH-VALUE episodes that lack them

These episodes have DR data and are significant conflicts but lack any women/children breakdown. Prioritize by data availability:

| Episode | Why valuable | Likely sources for demographic deaths |
|---------|-------------|--------------------------------------|
| **Stalingrad** | Famous battle, large civilian toll | Soviet-era demographic studies of Stalingrad casualties |
| **Siege of Budapest** | Large civilian toll (25k) | Hungarian Holocaust/siege memorial databases |
| **Battle of Berlin** | 30k civilian deaths | German civilian casualty studies (Overmans, etc.) |
| **Darfur episodes** | Major atrocity | UN CoI reports, Physicians for Human Rights surveys |
| **Rwanda genocide** | Paradigmatic case | Verwimp (2004) micro-demographics; gacaca records |
| **Srebrenica** (if present) | Gendered massacre | ICMP identification records (mostly adult males) |
| **Mosul 2016-17** | Recent, well-documented | AP investigations, Airwars, IBC |

---

## Computation Method

### Step 1: Demographic person-months (new estimates to create)

For each episode with demographic baseline data:

```
civ_person_months_women = civ_person_months × female_share
civ_person_months_children = civ_person_months × under18_share
civ_person_months_adult_male = civ_person_months × adult_male_share
```

**Adjustment needed**: If displacement was sex/age-differential, apply correction factors. E.g., if women and children were 80% of displaced population but 50% of baseline, the remaining-in-theater shares differ from baseline shares.

### Step 2: Demographic death rates

```
women_death_rate = civ_deaths_women / civ_person_months_women
children_death_rate = civ_deaths_children / civ_person_months_children
adult_male_death_rate = adult_male_civ_deaths / civ_person_months_adult_male
```

### Step 3: Demographic DRs

```
WC_DR_women = adult_male_death_rate / women_death_rate
WC_DR_children = adult_male_death_rate / children_death_rate
```

Interpretation:
- WC_DR_women > 1 → adult men dying faster than women (expected in targeted killings of military-age males)
- WC_DR_women < 1 → women dying faster (indiscriminate or targeting women)
- Same logic for children

### Step 4: Simplified fallback (no person-months needed)

If demographic person-months are too uncertain, a simpler metric:

```
children_share_of_deaths = civ_deaths_children / civ_deaths_direct
children_share_of_population = under18_population / total_civ_population
disproportionality_index = children_share_of_deaths / children_share_of_population
```

- Index > 1 → children overrepresented in deaths
- Index < 1 → children underrepresented
- Index = 1 → proportional

This only requires the demographic baseline (no person-months split), so it's feasible for more episodes.

---

## Data Model Changes

New metric names to add (no schema changes needed — `metric_name` is free-form):

```
civ_person_months_women          — female civilian person-months
civ_person_months_children_u18   — under-18 civilian person-months
civ_person_months_adult_male     — adult male civilian person-months
wc_dr_women                      — women demographic DR
wc_dr_children_u18               — children demographic DR
civ_deaths_adult_male_direct     — derived: total − women − children
disproportionality_children_u18  — simplified ratio (no person-months)
disproportionality_women         — simplified ratio (no person-months)
```

New claim variables to support:
```
female_population_share           — % female in theater population
under18_population_share          — % under 18 in theater population
total_civilian_population         — theater population (may already exist)
displacement_sex_age_differential — qualitative: "none observed" / "women+children overrepresented in displacement" / etc.
```

---

## Structural Challenges

1. **Age threshold inconsistency**: Standardize on under-18 where possible. For under-15 data (Sri Lanka), note the difference and don't mix with under-18 in comparisons.

2. **Double-counting**: Women under 18 may appear in both women and children counts. Verify per source whether "women" means adult women (18+) or all females. If "women" = all females, the categories overlap and `adult_male = total − women − children` is wrong. **Must check each source definition.**

3. **Combatant boundary**: Adult male civilians vs. combatants is the hardest line. Some sources exclude "military-age males" from civilian counts entirely. The women/children DR would be most robust for episodes where the civ/mil classification is well-established.

4. **Displacement differential**: Women and children often flee first, reducing their exposure. If 80% of the displaced are women/children, the remaining population skews heavily male. Using baseline shares without displacement adjustment would overestimate women/children person-months and thus underestimate their death rate (making things look safer for them than reality).

5. **Small numbers**: Episodes with <50 women or children deaths have wide statistical uncertainty. Flag episodes where demographic counts are too small for meaningful rate comparisons.

---

## Suggested Phasing

### Phase 1: Quick wins (disproportionality index only)
- For all 13 episodes with existing women/children counts
- Only need: demographic baseline population share per country/region
- UN World Population Prospects gives country-level age-sex pyramids — apply to theater
- Produces the simplified disproportionality index (no person-months split needed)
- GPT-Pro task: find under-18% and female% for each country-year

### Phase 2: Full demographic DR for best-documented episodes
- Start with Cast Lead + Protective Edge (PCBS data is excellent)
- Eastern Ghouta (OCHA profiles available)
- Great March of Return (well-documented protest demographics)
- Requires: displacement-adjusted demographic person-months
- GPT-Pro task: find sex/age-disaggregated displacement data

### Phase 3: Expand death count coverage
- Research women/children death breakdowns for major episodes that lack them
- Prioritize: Darfur, Rwanda, Mosul, Berlin, Stalingrad
- GPT-Pro task: systematic literature search for demographic casualty breakdowns

### Phase 4: Historical episodes
- WWII urban battles, Korean War, Vietnam — harder sources but high interest
- May require academic monographs rather than NGO databases
