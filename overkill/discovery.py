from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from overkill.relationships import DEFAULT_TAXONOMY_PATH, index_bundle_relationships, load_bundle_relationships
from overkill.validation import BundleValidationError, load_and_validate_bundle


_EPISODE_TYPE_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("massacre", ("massacre", "execution", "executions", "shootings", "pogrom")),
    ("siege", ("siege", "encirclement", "encircled", "blockade", "holdout")),
    ("uprising", ("intifada", "uprising", "revolt", "protest", "demonstration")),
    ("air_bombardment", ("airstrike", "air raid", "bombardment", "shelling", "artillery", "rocket")),
    ("occupation", ("occupation", "capture", "captured", "recapture", "fall of", "collapse", "take of")),
    ("evacuation", ("evacuation", "corridor", "withdrawal", "exodus")),
    ("urban_battle", ("urban", "city", "beirut", "seoul", "mariupol", "mosul", "aleppo", "grozny", "budapest")),
]

_EPISODE_TYPE_PRIORITY = {
    "massacre": 0,
    "siege": 1,
    "uprising": 2,
    "air_bombardment": 3,
    "occupation": 4,
    "evacuation": 5,
    "urban_battle": 6,
    "other": 7,
}

_QUALITY_RANK = {"A": 0, "B": 1, "C": 2, "D": 3, None: 4}

# ── Side-to-country normalization ──
# Maps freeform victim_side / inflicting_side strings to short country-like labels.
# Lookup is case-insensitive (keys stored lowercase).

_SIDE_COUNTRY_MAP: dict[str, str] = {
    # Gaza
    "palestinians in gaza": "Gaza",
    "palestinian armed groups": "Gaza",
    "palestinian armed groups and police-as-military scenario": "Gaza",
    "palestinian militants under broad official classification": "Gaza",
    # Palestine (broader)
    "palestinians in occupied territories": "Palestine",
    "palestinian civilians (west bank + east jerusalem)": "Palestine",
    "palestinian local armed civilians (east jerusalem)": "Palestine",
    "palestinian worshippers / civilians": "Palestine",
    "palestinian": "Palestine",
    "palestinians": "Palestine",
    "palestinian camp population and fighters": "Palestine",
    "palestinian and lebanese shiite civilians in sabra and shatila": "Palestine",
    "palestinian and lebanese residents of sabra and shatila": "Palestine",
    "palestinian/kurdish/syrian/lebanese muslim civilians in karantina": "Lebanon",
    # Israel
    "israeli forces": "Israel",
    "israeli security forces": "Israel",
    "israel/idf": "Israel",
    "israeli border police / israeli security forces": "Israel",
    "israeli security forces and israeli civilians": "Israel",
    "idf soldiers": "Israel",
    "israeli civilians in the oct. 7 southern-israel attack": "Israel",
    "israeli civilians": "Israel",
    "israeli": "Israel",
    "israel-side": "Israel",
    "israel": "Israel",
    # USA
    "united states": "USA",
    "u.s. forces": "USA",
    "u.s. marines": "USA",
    "u.s./un assault forces": "USA",
    "u.s. marine aircraft": "USA",
    "u.n./u.s. marine division": "USA",
    "us-led coalition": "USA",
    "us-led coalition and/or iraqi government forces": "USA",
    "u.s. assault force": "USA",
    "raf and usaaf": "UK/USA",
    # Russia
    "russian forces": "Russia",
    "russian military": "Russia",
    "russian soldiers": "Russia",
    "russian-syrian coalition": "Russia",
    # USSR / Soviet
    "soviet and afghan government forces": "USSR",
    "soviet-romanian besiegers": "USSR",
    "soviet civilians in stalingrad": "USSR",
    "leningrad civilians": "USSR",
    # NATO
    "nato": "NATO",
    # Germany
    "german luftwaffe": "Germany",
    "german forces (principally luftwaffe during opening bombardment)": "Germany",
    "german occupation forces and auxiliaries": "Germany",
    "population present in dresden proper": "Germany",
    # Japan
    "japan": "Japan",
    # China
    "china": "China",
    "chinese troops": "China",
    # Syria
    "syria": "Syria",
    "east aleppo civilians": "Syria",
    "aleppo civilians": "Syria",
    "eastern ghouta civilians": "Syria",
    "idlib civilians": "Syria",
    "raqqa civilians": "Syria",
    "syrian government forces and/or russian forces": "Syria",
    # Iraq
    "iraq": "Iraq",
    "iraqi civilians": "Iraq",
    "iraqi government / iraqi military": "Iraq",
    "mosul civilians": "Iraq",
    "west mosul civilians": "Iraq",
    "persons killed in halabja during the attack window": "Iraq",
    # Egypt
    "egypt": "Egypt",
    # Jordan
    "jordan": "Jordan",
    # Iran
    "iran": "Iran",
    # Myanmar
    "myanmar military and local militias": "Myanmar",
    "myanmar security forces": "Myanmar",
    "rohingya civilians": "Myanmar",
    "hindu civilians": "Myanmar",
    "alleged arsa / mobilized attackers": "Myanmar",
    "arsa": "Myanmar",
    # Lebanon
    "lebanese and palestinian civilians in west beirut": "Lebanon",
    "plo/pla/syrian armed personnel in west beirut": "Lebanon",
    "persons present in besieged beirut/west beirut": "Lebanon",
    "lebanese forces / phalangist militiamen": "Lebanon",
    "lebanese front militias": "Lebanon",
    "phalangist militia": "Lebanon",
    "christian militias with syrian army support": "Lebanon",
    "lebanon-side": "Lebanon",
    "hezbollah": "Lebanon",
    # Bosnia
    "bosniak civilians / non-soldiers as residually classified": "Bosnia",
    "bosniak soldiers / personnel coded as soldiers in bbd": "Bosnia",
    "bosnian muslim civilians in east mostar": "Bosnia",
    "bosnian muslim civilians in potočari and civilians mixed into the breakout column": "Bosnia",
    "bosnian muslim men and boys": "Bosnia",
    "bosnian muslim soldiers in the breakout column": "Bosnia",
    "bosnian muslims from the srebrenica enclave": "Bosnia",
    "army of bosnia and herzegovina (inside sarajevo)": "Bosnia",
    "bosnian serb forces": "Bosnian Serbs",
    "bosnian serb army and police forces": "Bosnian Serbs",
    "sarajevo romanija corps (army of republika srpska)": "Bosnian Serbs",
    # Serbia
    "serbian/yugoslav forces": "Serbia",
    "jna and serbian paramilitary forces": "Serbia",
    "vj and serbian moi": "Serbia",
    "vj/mup": "Serbia",
    # Kosovo
    "kla": "Kosovo",
    "kosovo albanian civilians": "Kosovo",
    "serb civilians": "Kosovo",
    "serbs and other non-kosovo albanian civilians": "Kosovo",
    "roma and other non-albanian civilians": "Kosovo",
    # Croatia
    "hospital evacuees from vukovar": "Croatia",
    # Rwanda
    "tutsi civilians in kibuye prefecture": "Rwanda",
    "kibuye prefectural authorities and aligned assailants: soldiers, police/gendarmes, interahamwe, and civilian attackers": "Rwanda",
    # Sudan
    "massalit and other non-arab civilians": "Sudan",
    "sudanese civilians": "Sudan",
    "rsf and allied arab militias": "Sudan",
    "rsf-janjaweed": "Sudan",
    # Yemen
    "civilians in aden": "Yemen",
    "civilians in marib": "Yemen",
    "houthi/saleh forces": "Yemen",
    "pro-hadi / southern resistance": "Yemen",
    "pro-hadi / southern resistance and coalition partners": "Saudi coalition",
    # Libya
    "misrata-held civilians": "Libya",
    "anti-qadhafi fighters in misrata": "Libya",
    "qadhafi-aligned forces": "Libya",
    # Indonesia / East Timor
    "east timorese civilians": "East Timor",
    "indonesian security forces and pro-indonesia militias": "Indonesia",
    # Hungary
    "budapest civilians": "Hungary",
    "budapest jewish civilians": "Hungary",
    "axis budapest garrison": "Hungary",
    "axis budapest defenders": "Hungary",
    "arrow cross party / hungarian fascist militias": "Hungary",
    # Poland
    "warsaw civilians (mostly poles, plus hidden jews not demonstrably in armed service)": "Poland",
    "warsaw civilians in left-bank warsaw": "Poland",
    # Ukraine
    "ukrainian civilians": "Ukraine",
    "ukrainian state forces": "Ukraine",
    # Korea
    "south korean civilians": "South Korea",
    "north korean military (kpa garrison)": "North Korea",
    "kpa": "North Korea",
    "rok army engineers": "South Korea",
    "military/combatant personnel in strict no gun ri micro-episode": "South Korea",
    "wolmido civilians": "South Korea",
    # Vietnam
    "huế civilian residents": "Vietnam",
    "huế civilian residents (mostly south vietnamese civilians)": "Vietnam",
    "vietnamese civilians at tong chup": "Vietnam",
    "pavn": "North Vietnam",
    "fall of saigon": "Vietnam",
    # Chechnya
    "civilians in staropromyslovski district": "Chechnya",
    "civilian children in chechnya": "Chechnya",
    "civilian women in chechnya": "Chechnya",
    "civilians in chechnya": "Chechnya",
    # Afghanistan
    "panjshiri civilians": "Afghanistan",
    "massoud-aligned mujahideen": "Afghanistan",
    # India
    "indian armed forces": "India",
    "indian security forces": "India",
    "armed defenders / militants inside the complex": "India",
    # Pakistan
    "pakistan / infiltrators": "Pakistan",
    # Nigeria
    "asaba civilians": "Nigeria",
    "nigerian federal forces / 2nd infantry division": "Nigeria",
    # Colombia
    "farc-ep": "Colombia",
    # Peru
    "pcp-sendero luminoso": "Peru",
    # El Salvador
    "salvadoran armed forces": "El Salvador",
    "fmln insurgents in the capital offensive": "El Salvador",
    # Somalia
    "somali mixed fighters/civilians": "Somalia",
    # ISIS
    "islamic state (isis)": "ISIS",
    # Marawi
    "aggregate_opposed_combatants": "Philippines",
    # Misc catch-alls for HVO
    "hvo (croat forces)": "Croatia",
}


# Shorten long / formal country names used in bundle metadata
_COUNTRY_SHORT_NAMES: dict[str, str] = {
    "Federal Republic of Yugoslavia": "Yugoslavia",
    "Ottoman Empire (present-day Turkey)": "Ottoman Empire",
    "Ottoman Syria (present-day Syria)": "Syria",
    "Soviet Union": "USSR",
    "South Vietnam (Republic of Vietnam)": "South Vietnam",
    "North Vietnam (Democratic Republic of Vietnam)": "North Vietnam",
    "British Hong Kong": "Hong Kong",
    "Bosnia and Herzegovina": "Bosnia",
    "North Macedonia": "N. Macedonia",
    "United States": "USA",
    "United Kingdom": "UK",
    "Republic of Korea": "South Korea",
    "Democratic People's Republic of Korea": "North Korea",
}


def _shorten_country(name: str | None) -> str | None:
    """Apply short-name mapping to a country string."""
    if not name:
        return name
    return _COUNTRY_SHORT_NAMES.get(name, name)


# Explicit side overrides for episodes where automatic attribution is wrong.
# Key is (bundle_id, episode_id).

_VICTIM_OVERRIDES: dict[tuple[str, str], str] = {
    ("bangladesh-war-1971", "bgd1971_dhaka_searchlight_opening"): "Bangladesh",
    ("battle-of-grozny-1994-1995", "gznA_citywide_aggregate"): "Chechnya",
    ("darfur-war-2003-present", "darfur_ep02_peak_2003-09_2004-03"): "Darfur",
    ("darfur-war-2003-present", "darfur_ep03_scaleup_2004-04_2004-12"): "Darfur",
    ("rohingya-crackdown-2016-2017", "rc17_a"): "Rohingya",
    ("six-day-war-1967", "sdw1967_westbank_ej"): "West Bank",
    ("sri-lanka-eelam-war-iv-2006-2009", "sl-ew4-e3"): "Tamil",
    ("sudan_conflicts_1983_present_repair", "ep_ardamata_2023_11_01_2023_11_10"): "Masalit",
    ("sudan_conflicts_1983_present_repair", "ep_elgeneina_2023_04_24_2023_06_22"): "Masalit",
    ("tigray-war-2020-2022", "tigray_e1_2020-11_2021-06"): "Tigray",
}

_INFLICTING_OVERRIDES: dict[tuple[str, str], str] = {
    ("afghanistan_war_2001_2021", "afg_2021_kabul_airport_abbey_gate"): "ISIS-K",
    ("bangladesh-war-1971", "bgd1971_dhaka_searchlight_opening"): "Pakistan",
    ("battle-of-grozny-1994-1995", "gznA_citywide_aggregate"): "Russia",
    ("battle-of-manila-1945", "bom45-citywide"): "Japan",
    ("battle-of-marawi-2017", "marawi_city_siege_and_clearance_2017"): "ISIS/Maute",
    ("darfur-war-2003-present", "darfur_ep02_peak_2003-09_2004-03"): "Sudan",
    ("darfur-war-2003-present", "darfur_ep03_scaleup_2004-04_2004-12"): "Sudan",
    ("gulf-war-1990-1991", "gw1990_1991_e2_air_campaign"): "USA",
    ("kosovo-war-1998-1999", "kw98_e2_kosovo_inside_nato_window"): "Serbia",
    ("libya-2011-nato-intervention", "libya2011_misrata_urban_siege"): "Gaddafi forces",
    ("nato-air-war-yugoslavia-1999", "nato-on-fry_1999-03-24_1999-06-09"): "NATO",
    ("october-7-attack-southern-israel-2023", "oct7_southern_israel_attack_immediate_retake_2023-10-07_2023-10-10"): "Hamas",
    ("palace-of-justice-siege-1985", "palace-of-justice-siege-1985-core"): "M-19 / Colombia",
    ("second_chechen_war_1999_2009", "scw2_ep02_open_war_chechnya"): "Russia",
    ("siege_of_budapest_1944_1945", "siege_of_budapest_1944_1945_ep1_city-siege"): "USSR",
    ("six-day-war-1967", "sdw1967_westbank_ej"): "Israel",
    ("sri-lanka-eelam-war-iv-2006-2009", "sl-ew4-e3"): "Sri Lanka",
    ("sudan_conflicts_1983_present_repair", "ep_ardamata_2023_11_01_2023_11_10"): "RSF",
    ("sudan_conflicts_1983_present_repair", "ep_elgeneina_2023_04_24_2023_06_22"): "RSF",
    ("tigray-war-2020-2022", "tigray_e1_2020-11_2021-06"): "Ethiopia",
    ("ww2_major_urban_battles_central_west_europe_1944_1945", "berlin_1945_city_battle"): "USSR",
    ("ww2_major_urban_battles_central_west_europe_1944_1945", "vienna_1945_city_battle"): "USSR",
    ("ww2_major_urban_battles_eastern_europe_1944_1945", "budapest_siege_1944_12_26_1945_02_13"): "USSR",
}


def _normalize_side_to_country(side: str | None) -> str | None:
    """Map a freeform side string to a short country-like label."""
    if not side:
        return None

    key = side.lower().strip()

    # 1. Explicit table lookup
    mapped = _SIDE_COUNTRY_MAP.get(key)
    if mapped:
        return mapped

    # 2. Pattern matching for common suffixes
    for suffix in (" forces", " military", " troops", " soldiers", " army"):
        if key.endswith(suffix):
            return _shorten_country(key[: -len(suffix)].strip().title())
    for suffix in (" civilians", " armed groups", " security forces"):
        if key.endswith(suffix):
            return _shorten_country(key[: -len(suffix)].strip().title())

    # 3. Return original string, shortened if possible
    return _shorten_country(side.strip())


def _extract_episode_sides(
    metric_rows: list[dict[str, Any]],
    fallback_countries: list[str] | None = None,
    *,
    bundle_id: str | None = None,
    episode_id: str | None = None,
) -> dict[str, str | None]:
    """Pull victim_country and inflicting_country from metric rows with smart fallbacks."""
    # Priority order for finding side strings across metric types
    _VICTIM_METRICS = ("dr_v1_direct", "civ_deaths_direct", "civ_person_months")
    _INFLICTING_METRICS = ("dr_v1_direct", "civ_deaths_direct", "mil_deaths_direct")

    def _first_side(field: str, preferred_metrics: tuple[str, ...]) -> str | None:
        for mn in preferred_metrics:
            for row in metric_rows:
                if row["metric_name"] == mn and row.get(field):
                    return row[field]
        # Any metric as last resort
        for row in metric_rows:
            if row.get(field):
                return row[field]
        return None

    victim_raw = _first_side("victim_side", _VICTIM_METRICS)
    inflicting_raw = _first_side("inflicting_side", _INFLICTING_METRICS)

    countries = fallback_countries or []
    key = (bundle_id, episode_id) if bundle_id and episode_id else None

    # Victim: explicit override > data > first country
    if key and key in _VICTIM_OVERRIDES:
        victim_country = _VICTIM_OVERRIDES[key]
    elif victim_raw:
        victim_country = _normalize_side_to_country(victim_raw)
    elif countries:
        victim_country = _shorten_country(countries[0])
    else:
        victim_country = None

    # Inflicting: explicit override > data > second country
    if key and key in _INFLICTING_OVERRIDES:
        inflicting_country = _INFLICTING_OVERRIDES[key]
    elif inflicting_raw:
        inflicting_country = _normalize_side_to_country(inflicting_raw)
    elif len(countries) >= 2 and countries[1] != countries[0]:
        inflicting_country = _shorten_country(countries[1])
    else:
        inflicting_country = None

    return {
        "victim_side_raw": victim_raw,
        "inflicting_side_raw": inflicting_raw,
        "victim_country": victim_country,
        "inflicting_country": inflicting_country,
    }


def _validate_dr_from_components(metric_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Recompute DR from component metrics; return validation info or None."""
    def _count_rows(name: str) -> int:
        return sum(1 for r in metric_rows if r["metric_name"] == name and r.get("value_best") is not None)

    def _best(name: str) -> float | None:
        for r in metric_rows:
            if r["metric_name"] == name and r.get("value_best") is not None:
                return float(r["value_best"])
        return None

    # Skip validation for multi-side episodes where component metrics have
    # multiple rows (e.g., Rohingya civilians + Hindu civilians as separate rows).
    # The DR may have been computed from a specific subset we can't infer.
    for mn in ("civ_deaths_direct", "mil_deaths_direct", "civ_person_months", "mil_person_months"):
        if _count_rows(mn) > 1:
            return None

    civ_d = _best("civ_deaths_direct")
    mil_d = _best("mil_deaths_direct")
    civ_pm = _best("civ_person_months")
    mil_pm = _best("mil_person_months")
    stored_dr = _best("dr_v1_direct")

    if not all(v is not None and v > 0 for v in [civ_d, mil_d, civ_pm, mil_pm]):
        return None

    mil_rate = mil_d / mil_pm
    civ_rate = civ_d / civ_pm
    computed = mil_rate / civ_rate

    result: dict[str, Any] = {"dr_v1_computed": round(computed, 6)}
    if stored_dr is not None and stored_dr > 0:
        ratio = computed / stored_dr
        result["stored_dr"] = stored_dr
        result["ratio_computed_to_stored"] = round(ratio, 4)
        result["formula_match"] = 0.85 <= ratio <= 1.15
        if ratio < 0.01 or ratio > 100:
            result["likely_inverted"] = True
    return result


def scan_bundle_root(bundle_root: str | Path) -> list[dict[str, Any]]:
    root = Path(bundle_root)
    if not root.exists():
        return []

    entries: list[dict[str, Any]] = []
    for path in sorted(child for child in root.iterdir() if child.is_dir()):
        entries.append(scan_bundle(path))
    return entries


def scan_bundle(bundle_path: str | Path) -> dict[str, Any]:
    path = Path(bundle_path)
    updated_at = _latest_mtime_iso(path)
    file_names = sorted(child.name for child in path.iterdir() if child.is_file()) if path.exists() else []

    try:
        result = load_and_validate_bundle(path)
    except BundleValidationError as exc:
        return {
            "bundle_id": path.name,
            "bundle_path": str(path),
            "status": "invalid",
            "updated_at": updated_at,
            "files": file_names,
            "error": str(exc),
        }

    source_catalog = {source.source_id: _serialize_source(source) for source in result.sources}
    claims_by_id = {claim.claim_id: claim for claim in result.claims}
    claims_by_episode: dict[str, list[dict[str, Any]]] = {}
    for claim in result.claims:
        claims_by_episode.setdefault(claim.episode_id, []).append(_serialize_claim(claim))

    estimates_by_episode: dict[str, dict[str, dict[str, Any]]] = {}
    estimate_rows_by_episode: dict[str, list[dict[str, Any]]] = {}
    for estimate in result.estimates:
        serialized_estimate = _serialize_estimate(
            estimate=estimate,
            claims_by_id=claims_by_id,
            source_catalog=source_catalog,
        )
        estimates_by_episode.setdefault(estimate.episode_id, {})[estimate.metric_name] = serialized_estimate
        estimate_rows_by_episode.setdefault(estimate.episode_id, []).append(serialized_estimate)

    open_question_counts: dict[str, int] = {}
    for question in result.open_questions:
        open_question_counts[question.episode_id] = open_question_counts.get(question.episode_id, 0) + 1

    episodes = []
    for episode in result.episodes:
        metrics = estimates_by_episode.get(episode.episode_id, {})
        metric_rows = sorted(
            estimate_rows_by_episode.get(episode.episode_id, []),
            key=lambda item: (
                item["metric_name"],
                item["inflicting_side"] or "",
                item["victim_side"] or "",
            ),
        )
        episode_claims = claims_by_episode.get(episode.episode_id, [])
        source_ledger = _build_episode_source_ledger(episode_claims, source_catalog)
        episode_types = _classify_episode_types(episode)
        readiness = _derive_episode_readiness(metrics, metric_rows, episode.full_estimate_completed, len(episode_claims))
        side_attribution_summary = _summarize_episode_side_attribution(episode_claims, metric_rows)
        proxy_limit_flags = _derive_episode_proxy_limit_flags(
            metrics=metrics,
            metric_rows=metric_rows,
            full_estimate_completed=episode.full_estimate_completed,
            readiness=readiness,
            side_attribution_summary=side_attribution_summary,
        )
        ep_countries = getattr(episode, "countries", None) or []
        bundle_countries = result.conflict.countries or []
        # Merge episode + bundle countries (deduplicated, episode order first)
        seen = set()
        merged_countries: list[str] = []
        for c in list(ep_countries) + list(bundle_countries):
            if c not in seen:
                seen.add(c)
                merged_countries.append(c)
        sides = _extract_episode_sides(
            metric_rows, merged_countries,
            bundle_id=path.name, episode_id=episode.episode_id,
        )
        dr_validation = _validate_dr_from_components(metric_rows)
        episodes.append(
            {
                "episode_id": episode.episode_id,
                "episode_name": episode.episode_name,
                "start_date": episode.start_date.isoformat(),
                "end_date": episode.end_date.isoformat() if episode.end_date is not None else None,
                "countries": ep_countries,
                "geographic_scope": episode.geographic_scope,
                "quality_tier": episode.quality_tier,
                "quality_note": episode.quality_note,
                "full_estimate_completed": episode.full_estimate_completed,
                "theater_description": episode.theater_description,
                "metrics": metrics,
                "metric_rows": metric_rows,
                "claim_count": len(episode_claims),
                "source_count": len(source_ledger),
                "source_ledger": source_ledger,
                "open_question_count": open_question_counts.get(episode.episode_id, 0),
                "episode_types": episode_types,
                "primary_episode_type": _primary_episode_type(episode_types),
                "readiness": readiness,
                "proxy_limit_flags": proxy_limit_flags,
                "side_attribution_summary": side_attribution_summary,
                "victim_country": sides["victim_country"],
                "inflicting_country": sides["inflicting_country"],
                "dr_validation": dr_validation,
            }
        )

    valid_dr_values = [
        metric["value_best"]
        for episode_metrics in estimates_by_episode.values()
        for metric_name, metric in episode_metrics.items()
        if metric_name == "dr_v1_direct" and metric["value_best"] is not None
    ]

    readiness_counts = _count_by_value(episode["readiness"] for episode in episodes)
    episode_type_counts = _count_by_value(
        episode_type
        for episode in episodes
        for episode_type in episode["episode_types"]
    )
    side_attribution_summary = _summarize_bundle_side_attribution(episodes)
    proxy_limit_flags = _derive_bundle_proxy_limit_flags(episodes, side_attribution_summary)

    return {
        "bundle_id": path.name,
        "bundle_path": str(path),
        "status": "valid",
        "updated_at": updated_at,
        "files": file_names,
        "conflict_id": result.conflict.conflict_id,
        "conflict_name": result.conflict.conflict_name,
        "aliases": result.conflict.aliases,
        "countries": result.conflict.countries,
        "regions": result.conflict.regions,
        "start_date": result.conflict.start_date.isoformat(),
        "end_date": result.conflict.end_date.isoformat() if result.conflict.end_date is not None else None,
        "notes": result.conflict.notes,
        "counts": {
            "episodes": len(result.episodes),
            "sources": len(result.sources),
            "claims": len(result.claims),
            "estimates": len(result.estimates),
            "assumptions": len(result.assumptions),
            "open_questions": len(result.open_questions),
        },
        "sources": _build_bundle_source_ledger(
            claims_by_episode=claims_by_episode,
            source_catalog=source_catalog,
        ),
        "estimated_episode_count": sum(1 for episode in result.episodes if episode.full_estimate_completed),
        "dr_range_best_values": {
            "min": min(valid_dr_values) if valid_dr_values else None,
            "max": max(valid_dr_values) if valid_dr_values else None,
        },
        "episodes": episodes,
        "readiness_counts": readiness_counts,
        "episode_type_counts": episode_type_counts,
        "side_attribution_summary": side_attribution_summary,
        "proxy_limit_flags": proxy_limit_flags,
    }


def read_active_target(prompt_path: str | Path) -> dict[str, Any] | None:
    path = _resolve_prompt_path(prompt_path)
    if not path.is_file():
        return None

    lines = path.read_text(encoding="utf-8").splitlines()
    target: dict[str, Any] = {}
    wanted = {
        "- In progress:": "conflict_name",
        "- Focus/theater/phase:": "focus",
        "- Date range:": "date_range",
        "- Working note:": "note",
    }
    for line in lines:
        for prefix, key in wanted.items():
            if line.startswith(prefix):
                target[key] = line[len(prefix) :].strip().replace("`", "")
    return target or None


def build_overview(
    bundle_root: str | Path,
    *,
    prompt_path: str | Path | None = None,
    taxonomy_path: str | Path = DEFAULT_TAXONOMY_PATH,
) -> dict[str, Any]:
    bundles = scan_bundle_root(bundle_root)
    active_target = read_active_target(prompt_path) if prompt_path is not None else None
    taxonomy_payload = load_bundle_relationships(taxonomy_path)
    taxonomy_index = index_bundle_relationships(taxonomy_payload)
    _annotate_bundles_with_taxonomy(bundles, taxonomy_index)
    valid_count = sum(1 for bundle in bundles if bundle["status"] == "valid")
    invalid_count = sum(1 for bundle in bundles if bundle["status"] == "invalid")
    best_supported_episodes = extract_best_supported_episodes_from_bundles(bundles)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "bundle_root": str(Path(bundle_root)),
        "active_target": active_target,
        "bundle_count": len(bundles),
        "valid_bundle_count": valid_count,
        "invalid_bundle_count": invalid_count,
        "taxonomy": _build_overview_taxonomy_summary(bundles, taxonomy_payload),
        "side_attribution_summary": _summarize_overview_side_attribution(bundles),
        "best_supported_episodes": best_supported_episodes,
        "bundles": bundles,
    }


def build_best_supported_episode_export(
    bundle_root: str | Path,
    *,
    prompt_path: str | Path | None = None,
    taxonomy_path: str | Path = DEFAULT_TAXONOMY_PATH,
) -> dict[str, Any]:
    overview = build_overview(bundle_root, prompt_path=prompt_path, taxonomy_path=taxonomy_path)
    return {
        "generated_at": overview["generated_at"],
        "bundle_root": overview["bundle_root"],
        "taxonomy": overview["taxonomy"],
        "episode_count": len(overview["best_supported_episodes"]),
        "episodes": overview["best_supported_episodes"],
    }


def extract_best_supported_episodes_from_bundles(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    episodes: list[dict[str, Any]] = []
    for bundle in bundles:
        if bundle.get("status") != "valid":
            continue
        if not bundle.get("public_canonical", True):
            continue
        for episode in bundle.get("episodes", []):
            if episode.get("readiness") not in {"publishable_dr", "publishable_fallback"}:
                continue
            if episode.get("quality_tier") not in {"A", "B", "C"}:
                continue
            episodes.append(
                {
                    "bundle_id": bundle["bundle_id"],
                    "conflict_id": bundle.get("conflict_id"),
                    "conflict_name": bundle.get("conflict_name"),
                    "bundle_public_visibility": bundle.get("public_visibility"),
                    "episode_id": episode["episode_id"],
                    "episode_name": episode["episode_name"],
                    "start_date": episode["start_date"],
                    "end_date": episode["end_date"],
                    "quality_tier": episode["quality_tier"],
                    "readiness": episode["readiness"],
                    "primary_episode_type": episode["primary_episode_type"],
                    "episode_types": episode["episode_types"],
                    "proxy_limit_flags": episode["proxy_limit_flags"],
                    "side_attribution_summary": episode["side_attribution_summary"],
                    "victim_country": episode.get("victim_country"),
                    "inflicting_country": episode.get("inflicting_country"),
                    "dr_v1_direct": episode["metrics"].get("dr_v1_direct"),
                    "dr_midpoint_fallback": episode["metrics"].get("dr_midpoint_fallback"),
                    "dr_validation": episode.get("dr_validation"),
                }
            )

    return sorted(
        episodes,
        key=lambda item: (
            _QUALITY_RANK.get(item["quality_tier"], 4),
            item["bundle_id"],
            item["episode_name"].lower(),
        ),
    )


def _annotate_bundles_with_taxonomy(bundles: list[dict[str, Any]], taxonomy_index: dict[str, Any]) -> None:
    for bundle in bundles:
        bundle.update(_derive_bundle_taxonomy_metadata(bundle, taxonomy_index))


def _derive_bundle_taxonomy_metadata(bundle: dict[str, Any], taxonomy_index: dict[str, Any]) -> dict[str, Any]:
    bundle_id = bundle["bundle_id"]
    role_row = taxonomy_index["roles_by_bundle"].get(bundle_id)
    relations = taxonomy_index["relations_by_bundle"].get(bundle_id, [])
    incoming_relations = taxonomy_index["relations_by_other_bundle"].get(bundle_id, [])
    preferred_over = [
        relation
        for relation in relations
        if relation["relation_type"] in {"supersedes_bundle", "supersedes_episode"}
    ]
    defer_to = [
        relation
        for relation in relations
        if relation["relation_type"] == "prefer_parent_bundle"
    ]
    superseded_by = [
        relation
        for relation in incoming_relations
        if relation["relation_type"] == "supersedes_bundle"
    ]

    if bundle.get("status") != "valid":
        public_visibility = "invalid"
        public_canonical = False
    elif superseded_by:
        public_visibility = "superseded"
        public_canonical = False
    elif role_row is not None and role_row["role"] == "umbrella":
        public_visibility = "umbrella"
        public_canonical = False
    elif defer_to:
        public_visibility = "demoted"
        public_canonical = False
    else:
        public_visibility = "canonical"
        public_canonical = True

    return {
        "bundle_role": role_row["role"] if role_row is not None else None,
        "bundle_role_note": role_row["notes"] if role_row is not None else None,
        "provisional": bundle_id in taxonomy_index["provisional_bundle_ids"],
        "relations": relations,
        "preferred_over": preferred_over,
        "defer_to": defer_to,
        "superseded_by": superseded_by,
        "public_visibility": public_visibility,
        "public_canonical": public_canonical,
    }


def _metric_row_has_publishable_values(metric_row: dict[str, Any]) -> bool:
    return any(metric_row.get(key) is not None for key in ("value_low", "value_best", "value_high"))


def _episode_has_publishable_metric(metric_rows: list[dict[str, Any]], metric_name: str) -> bool:
    return any(
        metric_row["metric_name"] == metric_name and _metric_row_has_publishable_values(metric_row)
        for metric_row in metric_rows
    )


def _summarize_episode_side_attribution(
    episode_claims: list[dict[str, Any]],
    metric_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    claim_victim = sum(1 for claim in episode_claims if claim.get("victim_side"))
    claim_inflicting = sum(1 for claim in episode_claims if claim.get("inflicting_side"))
    estimate_victim = sum(1 for estimate in metric_rows if estimate.get("victim_side"))
    estimate_inflicting = sum(1 for estimate in metric_rows if estimate.get("inflicting_side"))
    return {
        "claim_count": len(episode_claims),
        "estimate_count": len(metric_rows),
        "claims_with_victim_side": claim_victim,
        "claims_with_inflicting_side": claim_inflicting,
        "estimates_with_victim_side": estimate_victim,
        "estimates_with_inflicting_side": estimate_inflicting,
        "has_any_side_attribution": any([claim_victim, claim_inflicting, estimate_victim, estimate_inflicting]),
        "has_inflicting_side": any([claim_inflicting, estimate_inflicting]),
    }


def _derive_episode_readiness(
    metrics: dict[str, dict[str, Any]],
    metric_rows: list[dict[str, Any]],
    full_estimate_completed: bool,
    claim_count: int,
) -> str:
    if full_estimate_completed and _episode_has_publishable_metric(metric_rows, "dr_v1_direct"):
        return "publishable_dr"
    if full_estimate_completed and _episode_has_publishable_metric(metric_rows, "dr_midpoint_fallback"):
        return "publishable_fallback"
    if metrics or claim_count > 0:
        return "partial_estimate_only"
    return "context_only"


def _derive_episode_proxy_limit_flags(
    *,
    metrics: dict[str, dict[str, Any]],
    metric_rows: list[dict[str, Any]],
    full_estimate_completed: bool,
    readiness: str,
    side_attribution_summary: dict[str, Any],
) -> list[str]:
    flags: list[str] = []
    if not full_estimate_completed:
        flags.append("partial_episode")
    if readiness not in {"publishable_dr", "publishable_fallback"}:
        flags.append("publishable_dr_missing")
    if not side_attribution_summary["has_any_side_attribution"]:
        flags.append("side_attribution_missing")
    if not (
        _episode_has_publishable_metric(metric_rows, "mil_person_months")
        and _episode_has_publishable_metric(metric_rows, "civ_person_months")
    ):
        flags.append("denominator_missing_or_weak")
    if _episode_has_publishable_metric(metric_rows, "unknown_deaths_direct"):
        flags.append("unknown_status_present")
    if any(row["metric_name"] == "dr_midpoint_fallback" for row in metric_rows):
        flags.append("fallback_metric_present")
    if any(
        token in " ".join(
            str(value).lower()
            for value in (
                metrics.get("dr_v1_direct", {}).get("uncertainty_note"),
                metrics.get("dr_midpoint_fallback", {}).get("uncertainty_note"),
                metrics.get("dr_v1_direct", {}).get("quality_note"),
                metrics.get("dr_midpoint_fallback", {}).get("quality_note"),
            )
            if value
        )
        for token in ("indirect", "starvation", "deprivation", "famine", "siege")
    ):
        flags.append("indirect_harm_outside_baseline")
    return flags


def _summarize_bundle_side_attribution(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "episode_count": len(episodes),
        "episodes_with_any_side_attribution": sum(
            1 for episode in episodes if episode["side_attribution_summary"]["has_any_side_attribution"]
        ),
        "episodes_with_inflicting_side": sum(
            1 for episode in episodes if episode["side_attribution_summary"]["has_inflicting_side"]
        ),
    }


def _derive_bundle_proxy_limit_flags(
    episodes: list[dict[str, Any]],
    side_attribution_summary: dict[str, Any],
) -> list[str]:
    flags: list[str] = []
    if not any(episode["readiness"] in {"publishable_dr", "publishable_fallback"} for episode in episodes):
        flags.append("no_publishable_dr")
    if side_attribution_summary["episodes_with_any_side_attribution"] == 0:
        flags.append("side_attribution_missing")
    if episodes and all("denominator_missing_or_weak" in episode["proxy_limit_flags"] for episode in episodes):
        flags.append("denominator_missing_or_weak")
    if episodes and any("indirect_harm_outside_baseline" in episode["proxy_limit_flags"] for episode in episodes):
        flags.append("indirect_harm_outside_baseline")
    return flags


def _classify_episode_types(episode: Any) -> list[str]:
    haystack = " ".join(
        str(value).lower()
        for value in (
            episode.episode_name,
            episode.geographic_scope,
            episode.theater_description,
            episode.geometry_method_note,
            episode.split_reason,
            *episode.admin_units,
        )
        if value
    )
    matches = [
        episode_type
        for episode_type, keywords in _EPISODE_TYPE_RULES
        if any(keyword in haystack for keyword in keywords)
    ]
    return matches or ["other"]


def _primary_episode_type(episode_types: list[str]) -> str:
    return sorted(episode_types, key=lambda episode_type: _EPISODE_TYPE_PRIORITY.get(episode_type, 99))[0]


def _count_by_value(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _summarize_overview_side_attribution(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    valid_bundles = [bundle for bundle in bundles if bundle.get("status") == "valid"]
    return {
        "bundle_count": len(valid_bundles),
        "bundles_with_any_side_attribution": sum(
            1
            for bundle in valid_bundles
            if bundle.get("side_attribution_summary", {}).get("episodes_with_any_side_attribution", 0) > 0
        ),
        "bundles_with_inflicting_side": sum(
            1
            for bundle in valid_bundles
            if bundle.get("side_attribution_summary", {}).get("episodes_with_inflicting_side", 0) > 0
        ),
        "episode_count": sum(bundle.get("counts", {}).get("episodes", 0) for bundle in valid_bundles),
        "episodes_with_any_side_attribution": sum(
            bundle.get("side_attribution_summary", {}).get("episodes_with_any_side_attribution", 0)
            for bundle in valid_bundles
        ),
        "episodes_with_inflicting_side": sum(
            bundle.get("side_attribution_summary", {}).get("episodes_with_inflicting_side", 0)
            for bundle in valid_bundles
        ),
    }


def _build_overview_taxonomy_summary(bundles: list[dict[str, Any]], taxonomy_payload: dict[str, Any]) -> dict[str, Any]:
    valid_bundles = [bundle for bundle in bundles if bundle.get("status") == "valid"]
    return {
        "version": taxonomy_payload.get("version"),
        "updated_at": taxonomy_payload.get("updated_at"),
        "provisional_bundle_count": len(taxonomy_payload.get("provisional_bundle_ids", [])),
        "umbrella_bundle_count": sum(
            1 for row in taxonomy_payload.get("bundle_roles", []) if row.get("role") == "umbrella"
        ),
        "public_canonical_bundle_count": sum(1 for bundle in valid_bundles if bundle.get("public_canonical")),
        "demoted_bundle_count": sum(1 for bundle in valid_bundles if bundle.get("public_visibility") == "demoted"),
        "superseded_bundle_count": sum(1 for bundle in valid_bundles if bundle.get("public_visibility") == "superseded"),
    }


def _latest_mtime_iso(path: Path) -> str | None:
    if not path.exists():
        return None
    mtimes = [child.stat().st_mtime for child in path.rglob("*") if child.exists()]
    if not mtimes:
        return None
    return datetime.fromtimestamp(max(mtimes), UTC).isoformat()


def _resolve_prompt_path(prompt_path: str | Path) -> Path:
    requested = Path(prompt_path)
    candidates = [requested]
    if requested.name == "gptpro.md":
        candidates.append(requested.parent / "do" / "gptpro.md")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return requested


def _serialize_source(source: Any) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "citation_short": source.citation_short,
        "title": source.title,
        "author_or_org": source.author_or_org,
        "year": source.year,
        "source_type": source.source_type,
        "url": str(source.url) if source.url is not None else None,
        "pages_or_sections": source.pages_or_sections,
        "geographic_scope": source.geographic_scope,
        "date_scope": source.date_scope,
        "variables_supported": source.variables_supported,
        "strengths": source.strengths,
        "limitations": source.limitations,
        "notes": source.notes,
    }


def _serialize_claim(claim: Any) -> dict[str, Any]:
    return {
        "claim_id": claim.claim_id,
        "episode_id": claim.episode_id,
        "source_id": claim.source_id,
        "variable_name": claim.variable_name,
        "population_class": claim.population_class,
        "victim_side": claim.victim_side,
        "inflicting_side": claim.inflicting_side,
        "death_type": claim.death_type,
        "start_date": claim.start_date.isoformat(),
        "end_date": claim.end_date.isoformat(),
        "geographic_scope": claim.geographic_scope,
        "value_low": claim.value_low,
        "value_best": claim.value_best,
        "value_high": claim.value_high,
        "unit": claim.unit,
        "estimate_method": claim.estimate_method,
        "excerpt": claim.excerpt,
        "pages_or_sections": claim.pages_or_sections,
        "transform_note": claim.transform_note,
        "confidence_note": claim.confidence_note,
    }


def _serialize_estimate(
    *,
    estimate: Any,
    claims_by_id: dict[str, Any],
    source_catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_refs: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    for claim_id in estimate.input_claim_ids:
        claim = claims_by_id.get(claim_id)
        if claim is None or claim.source_id in seen_source_ids:
            continue
        seen_source_ids.add(claim.source_id)
        source = source_catalog.get(claim.source_id)
        if source is None:
            continue
        source_refs.append(
            {
                "source_id": source["source_id"],
                "citation_short": source["citation_short"],
                "source_type": source["source_type"],
                "url": source["url"],
            }
        )

    return {
        "metric_name": estimate.metric_name,
        "victim_side": estimate.victim_side,
        "inflicting_side": estimate.inflicting_side,
        "value_low": estimate.value_low,
        "value_best": estimate.value_best,
        "value_high": estimate.value_high,
        "unit": estimate.unit,
        "estimate_method": estimate.estimate_method,
        "quality_tier": estimate.quality_tier,
        "unknown_status_rule": estimate.unknown_status_rule,
        "uncertainty_note": estimate.uncertainty_note,
        "quality_note": estimate.quality_note,
        "formula_note": estimate.formula_note,
        "input_claim_ids": estimate.input_claim_ids,
        "source_refs": source_refs,
    }


def _build_episode_source_ledger(
    episode_claims: list[dict[str, Any]],
    source_catalog: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    ledger: dict[str, dict[str, Any]] = {}
    for claim in episode_claims:
        source = source_catalog.get(claim["source_id"])
        if source is None:
            continue
        entry = ledger.setdefault(
            source["source_id"],
            {
                **source,
                "claim_count": 0,
                "variables": [],
                "claims": [],
            },
        )
        entry["claim_count"] += 1
        if claim["variable_name"] not in entry["variables"]:
            entry["variables"].append(claim["variable_name"])
        entry["claims"].append(claim)

    return sorted(ledger.values(), key=lambda item: item["source_id"])


def _build_bundle_source_ledger(
    *,
    claims_by_episode: dict[str, list[dict[str, Any]]],
    source_catalog: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    ledger: dict[str, dict[str, Any]] = {}
    for episode_id, claims in claims_by_episode.items():
        for claim in claims:
            source = source_catalog.get(claim["source_id"])
            if source is None:
                continue
            entry = ledger.setdefault(
                source["source_id"],
                {
                    **source,
                    "claim_count": 0,
                    "episode_ids": [],
                    "variables": [],
                },
            )
            entry["claim_count"] += 1
            if episode_id not in entry["episode_ids"]:
                entry["episode_ids"].append(episode_id)
            if claim["variable_name"] not in entry["variables"]:
                entry["variables"].append(claim["variable_name"])

    return sorted(ledger.values(), key=lambda item: item["source_id"])
