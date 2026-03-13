/* ── SVG Icon System ── */

const ICONS = {
  "chevron-left": `<path d="M15 18l-6 6 6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>`,
  "chevron-right": `<path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>`,
  "globe": `<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none"/><path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" stroke="currentColor" stroke-width="2" fill="none"/>`,
  "play": `<polygon points="5,3 19,12 5,21" stroke="currentColor" stroke-width="2" stroke-linejoin="round" fill="currentColor"/>`,
  "pause": `<rect x="6" y="4" width="4" height="16" rx="1" fill="currentColor"/><rect x="14" y="4" width="4" height="16" rx="1" fill="currentColor"/>`,
  "x": `<path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>`,
  "menu": `<path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>`,
  "search": `<circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2" fill="none"/><path d="M21 21l-4.35-4.35" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>`,
  "external-link": `<path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>`,
  "folder": `<path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>`,
  "clock": `<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none"/><path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>`,
  "bar-chart": `<path d="M12 20V10M18 20V4M6 20v-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>`,
  "file-text": `<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>`,
  "sun": `<circle cx="12" cy="12" r="5" stroke="currentColor" stroke-width="2" fill="none"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>`,
  "moon": `<path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>`,
};

export function icon(name, size = 18) {
  const paths = ICONS[name];
  if (!paths) return "";
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true">${paths}</svg>`;
}

export const CORE_METRICS = [
  "dr_v1_direct",
  "civ_deaths_direct",
  "mil_deaths_direct",
  "unknown_deaths_direct",
  "civ_person_months",
  "mil_person_months",
];

const CORE_ORDER = new Map(CORE_METRICS.map((name, index) => [name, index]));

const TIER_ORDER = ["A", "B", "C", "D"];

export const GROUP_META = {
  core: { label: "Core estimates", description: "Main direct-ratio and numerator/denominator outputs." },
  subgroups: { label: "Subgroups", description: "Women, children, and other subgroup slices." },
  casualties: { label: "Casualties", description: "Injuries and total casualties alongside deaths." },
  audit: { label: "Audit / fallback", description: "Fallback or audit-style estimates." },
};

export const METRIC_META = {
  dr_v1_direct: { label: "Relative risk", shortLabel: "RR", group: "core" },
  civ_deaths_direct: { label: "Civilian deaths", shortLabel: "Civilian deaths", group: "core" },
  mil_deaths_direct: { label: "Military deaths", shortLabel: "Military deaths", group: "core" },
  unknown_deaths_direct: { label: "Unknown-status deaths", shortLabel: "Unknown deaths", group: "core" },
  civ_person_months: { label: "Civilian person-months", shortLabel: "Civilian PM", group: "core" },
  mil_person_months: { label: "Military person-months", shortLabel: "Military PM", group: "core" },
  dr_midpoint_fallback: { label: "Midpoint fallback ratio", shortLabel: "Fallback DR", group: "audit" },
  civ_deaths_women_direct: { label: "Civilian deaths: women", shortLabel: "Women deaths", group: "subgroups" },
  civ_deaths_children_u18_direct: { label: "Civilian deaths: children under 18", shortLabel: "Children <18", group: "subgroups" },
  civ_deaths_children_u15_direct: { label: "Civilian deaths: children under 15", shortLabel: "Children <15", group: "subgroups" },
  civ_casualties_direct: { label: "Civilian casualties", shortLabel: "Civilian casualties", group: "casualties" },
  civ_injuries_direct: { label: "Civilian injuries", shortLabel: "Civilian injuries", group: "casualties" },
  mil_casualties_direct: { label: "Military casualties", shortLabel: "Military casualties", group: "casualties" },
  mil_injuries_direct: { label: "Military injuries", shortLabel: "Military injuries", group: "casualties" },
};

const numberFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
const oneDecimalFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });
const threeDecimalFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 });
const fourDecimalFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 4 });

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function attr(value) {
  return escapeHtml(value);
}

export function isPresent(value) {
  return value !== null && value !== undefined && value !== "";
}

export function isRatioMetric(metricName) {
  return metricName?.startsWith("dr_");
}

export function metricGroup(metricName) {
  if (METRIC_META[metricName]?.group) return METRIC_META[metricName].group;
  if (!metricName) return "core";
  if (metricName === "dr_midpoint_fallback" || metricName.includes("audit") || metricName.includes("mortality")) {
    return "audit";
  }
  if (metricName.includes("_women_") || metricName.includes("_children_")) {
    return "subgroups";
  }
  if (metricName.includes("_casualties_") || metricName.includes("_injuries_")) {
    return "casualties";
  }
  return "core";
}

export function metricLabel(metricName) {
  return METRIC_META[metricName]?.label ?? titleCase(metricName.replaceAll("_", " "));
}

export function metricShortLabel(metricName) {
  return METRIC_META[metricName]?.shortLabel ?? metricLabel(metricName);
}

export function titleCase(value) {
  return String(value ?? "")
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function metricKey(metric) {
  return [
    metric?.metric_name ?? "",
    metric?.victim_side ?? "",
    metric?.inflicting_side ?? "",
  ].join("::");
}

export function compareMetricRows(a, b) {
  const aGroup = metricGroup(a.metric_name);
  const bGroup = metricGroup(b.metric_name);
  const groupOrder = ["core", "subgroups", "casualties", "audit"];
  const groupIndex = groupOrder.indexOf(aGroup) - groupOrder.indexOf(bGroup);
  if (groupIndex !== 0) return groupIndex;

  const aCore = CORE_ORDER.has(a.metric_name) ? CORE_ORDER.get(a.metric_name) : 999;
  const bCore = CORE_ORDER.has(b.metric_name) ? CORE_ORDER.get(b.metric_name) : 999;
  if (aCore !== bCore) return aCore - bCore;

  const aName = metricLabel(a.metric_name);
  const bName = metricLabel(b.metric_name);
  const byName = aName.localeCompare(bName);
  if (byName !== 0) return byName;

  const byVictim = (a.victim_side || "").localeCompare(b.victim_side || "");
  if (byVictim !== 0) return byVictim;

  return (a.inflicting_side || "").localeCompare(b.inflicting_side || "");
}

export function formatMetricNumber(value, metricName) {
  if (!isFiniteNumber(value)) return "—";
  const numeric = Number(value);

  if (isRatioMetric(metricName)) {
    const absolute = Math.abs(numeric);
    if (absolute >= 10) return oneDecimalFormatter.format(numeric);
    if (absolute >= 1) return threeDecimalFormatter.format(numeric);
    return fourDecimalFormatter.format(numeric);
  }

  if (Math.abs(numeric) >= 1000) return numberFormatter.format(numeric);
  if (Number.isInteger(numeric)) return numberFormatter.format(numeric);
  return oneDecimalFormatter.format(numeric);
}

export function formatMetricRange(metric) {
  if (!metric) return "No estimate";
  const low = metric.value_low;
  const best = metric.value_best;
  const high = metric.value_high;
  const metricName = metric.metric_name;

  if (!isFiniteNumber(low) && !isFiniteNumber(best) && !isFiniteNumber(high)) {
    return "No estimate in export";
  }

  const lowText = formatMetricNumber(low, metricName);
  const bestText = formatMetricNumber(best, metricName);
  const highText = formatMetricNumber(high, metricName);

  if (isFiniteNumber(low) && isFiniteNumber(best) && isFiniteNumber(high)) {
    return `${lowText} – ${highText} · best ${bestText}`;
  }
  if (isFiniteNumber(best)) return `Best ${bestText}`;
  if (isFiniteNumber(low) && isFiniteNumber(high)) return `${lowText} – ${highText}`;
  if (isFiniteNumber(low)) return `Low ${lowText}`;
  return `High ${highText}`;
}

export function formatPrimaryMetricValue(metric) {
  if (!metric) return "—";
  if (isFiniteNumber(metric.value_best)) return formatMetricNumber(metric.value_best, metric.metric_name);
  if (isFiniteNumber(metric.value_low) && isFiniteNumber(metric.value_high)) {
    return `${formatMetricNumber(metric.value_low, metric.metric_name)} – ${formatMetricNumber(metric.value_high, metric.metric_name)}`;
  }
  if (isFiniteNumber(metric.value_low)) return formatMetricNumber(metric.value_low, metric.metric_name);
  if (isFiniteNumber(metric.value_high)) return formatMetricNumber(metric.value_high, metric.metric_name);
  return "—";
}

export function formatDate(value, { month = "short", day = "numeric", year = "numeric" } = {}) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return escapeHtml(value);
  return new Intl.DateTimeFormat(undefined, { month, day, year }).format(date);
}

export function formatDateRange(startDate, endDate) {
  if (!startDate && !endDate) return "No date range";
  if (startDate && !endDate) return `${formatDate(startDate)} onward`;
  if (!startDate && endDate) return `Until ${formatDate(endDate)}`;
  return `${formatDate(startDate)} – ${formatDate(endDate)}`;
}

export function formatUpdatedAt(value) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return escapeHtml(value);
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

export function ratioLabel(range) {
  if (!range || !isFiniteNumber(range.min) || !isFiniteNumber(range.max)) return "No DR yet";
  const minText = formatMetricNumber(range.min, "dr_v1_direct");
  const maxText = formatMetricNumber(range.max, "dr_v1_direct");
  return minText === maxText ? minText : `${minText} – ${maxText}`;
}

export function safeUrl(value) {
  if (!value || typeof value !== "string") return null;
  try {
    const url = new URL(value, window.location.href);
    return /^https?:$/i.test(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

export function coveragePercent(part, total) {
  if (!total) return 0;
  return Math.max(0, Math.min(100, Math.round((Number(part) / Number(total)) * 100)));
}

export function qualityTone(tier) {
  if (tier === "A" || tier === "B") return "success";
  if (tier === "C") return "warning";
  if (tier === "D") return "danger";
  return "muted";
}

export function qualityBand(episodes = []) {
  const available = episodes
    .map((episode) => episode?.quality_tier)
    .filter((tier) => TIER_ORDER.includes(tier))
    .sort((a, b) => TIER_ORDER.indexOf(a) - TIER_ORDER.indexOf(b));

  if (!available.length) return null;
  const best = available[0];
  const worst = available[available.length - 1];
  return best === worst ? best : `${best}–${worst}`;
}

export function bundleFeatureFlags(bundle) {
  const episodes = bundle?.episodes || [];
  return {
    hasSideMetrics: episodes.some((episode) =>
      (episode.metric_rows || []).some((metric) => isPresent(metric.victim_side) || isPresent(metric.inflicting_side)),
    ),
    hasSubgroups: episodes.some((episode) =>
      (episode.metric_rows || []).some((metric) => metricGroup(metric.metric_name) === "subgroups"),
    ),
    hasCasualties: episodes.some((episode) =>
      (episode.metric_rows || []).some((metric) => metricGroup(metric.metric_name) === "casualties"),
    ),
    hasAudit: episodes.some((episode) =>
      (episode.metric_rows || []).some((metric) => metricGroup(metric.metric_name) === "audit"),
    ),
  };
}

export function availableGroups(episode) {
  if (!episode) return ["core"];
  const groups = new Set((episode.metric_rows || []).map((metric) => metric.group));
  groups.add("core");
  return ["core", "subgroups", "casualties", "audit"].filter((group) => groups.has(group));
}

export function buildLayerTiles(episode, group) {
  if (!episode) return [];

  const rows = (episode.metric_rows || []).filter((metric) => metric.group === group);

  if (group !== "core") return rows;

  const byName = new Map();
  for (const row of rows) {
    if (!byName.has(row.metric_name)) byName.set(row.metric_name, []);
    byName.get(row.metric_name).push(row);
  }

  const ordered = [];
  for (const metricName of CORE_METRICS) {
    const matches = byName.get(metricName) || [];
    if (matches.length) {
      ordered.push(...matches);
    } else {
      ordered.push({
        __missing: true,
        metric_name: metricName,
        key: `missing::${metricName}`,
      });
    }
  }

  for (const row of rows) {
    if (!CORE_ORDER.has(row.metric_name)) ordered.push(row);
  }

  return ordered;
}

export function findMetricByKey(metrics, key) {
  return (metrics || []).find((metric) => metric.key === key) || null;
}

export function defaultMetricForGroup(episode, group) {
  const rows = (episode?.metric_rows || []).filter((metric) => metric.group === group);
  if (!rows.length) return null;

  const preferred =
    rows.find((metric) => metric.metric_name === "dr_v1_direct" && !metric.victim_side && !metric.inflicting_side) ||
    rows.find((metric) => metric.metric_name === "dr_v1_direct") ||
    rows[0];

  return preferred;
}

export function defaultEpisode(bundle) {
  const episodes = bundle?.episodes || [];
  return episodes.find((episode) => (episode.metric_rows || []).length > 0) || episodes[0] || null;
}

export function defaultBundle(bundles) {
  return bundles.find((bundle) => bundle.is_active_target) || bundles[0] || null;
}

export function sourceClaimsForMetric(source, metric) {
  if (!source?.claims?.length) return [];
  if (!metric?.input_claim_ids?.length) return source.claims;
  const wantedIds = new Set(metric.input_claim_ids);
  return source.claims.filter((claim) => wantedIds.has(claim.claim_id));
}

export function relatedSourceIds(metric) {
  return new Set((metric?.source_refs || []).map((source) => source.source_id));
}

export function sortSourcesForMetric(sources, metric) {
  const related = relatedSourceIds(metric);
  return [...(sources || [])].sort((a, b) => {
    const aRank = related.has(a.source_id) ? 0 : 1;
    const bRank = related.has(b.source_id) ? 0 : 1;
    if (aRank !== bRank) return aRank - bRank;
    return (b.claim_count || 0) - (a.claim_count || 0) || String(a.citation_short || a.source_id).localeCompare(String(b.citation_short || b.source_id));
  });
}

export function bestPosition(metric) {
  if (!metric || !isFiniteNumber(metric.value_best)) return "50%";
  const low = isFiniteNumber(metric.value_low) ? Number(metric.value_low) : null;
  const high = isFiniteNumber(metric.value_high) ? Number(metric.value_high) : null;
  const best = Number(metric.value_best);

  if (low === null || high === null || high === low) return "50%";
  const ratio = Math.max(0, Math.min(1, (best - low) / (high - low)));
  return `${Math.round(ratio * 100)}%`;
}

export function sourceScopeLabel(scope) {
  return scope === "bundle" ? "Conflict-wide" : "Episode";
}

export function compactList(items = []) {
  return items.filter(Boolean).join(", ");
}

export function previewText(value, fallback = "No note provided in this export.") {
  if (!value) return fallback;
  const normalized = String(value).trim().replace(/\s+/g, " ");
  return normalized.length > 190 ? `${normalized.slice(0, 187)}…` : normalized;
}

export function isFiniteNumber(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}
