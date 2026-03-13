import {
  CORE_METRICS,
  bundleFeatureFlags,
  compareMetricRows,
  coveragePercent,
  defaultBundle,
  metricGroup,
  metricKey,
  qualityBand,
} from "./utils.js";

const DATA_PATHS = [
  "../data/index/bundles.json",
  "./data/bundles.json",
  "../data/bundles.json",
  "./bundles.json",
];

export async function loadOverview() {
  let lastError = null;

  for (const path of DATA_PATHS) {
    try {
      const response = await fetch(path, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status} while loading ${path}`);
      }

      return await response.json();
    } catch (error) {
      lastError = error;
    }
  }

  throw new Error(
    `Could not load bundle data. Checked ${DATA_PATHS.join(" and ")}. ${
      lastError?.message || "Unknown fetch error."
    }`,
  );
}

export function prepareOverview(raw) {
  const bundles = (raw?.bundles || [])
    .map((bundle) => prepareBundle(bundle, raw?.active_target))
    .sort((a, b) => String(a.conflict_name || a.bundle_id).localeCompare(String(b.conflict_name || b.bundle_id)));

  return {
    ...raw,
    bundles,
    default_bundle_id: defaultBundle(bundles)?.bundle_id ?? null,
  };
}

function prepareBundle(bundle, activeTarget) {
  const episodes = (bundle?.episodes || []).map(prepareEpisode);

  const normalizedActive = normalize(activeTarget?.conflict_name);
  const normalizedName = normalize(bundle?.conflict_name);
  const normalizedId = normalize(bundle?.bundle_id);

  return {
    ...bundle,
    episodes,
    estimated_ratio: coveragePercent(bundle?.estimated_episode_count || 0, bundle?.counts?.episodes || 0),
    quality_band: qualityBand(episodes),
    features: bundleFeatureFlags({ ...bundle, episodes }),
    is_active_target:
      Boolean(normalizedActive) &&
      (normalizedName.includes(normalizedActive) ||
        normalizedActive.includes(normalizedName) ||
        normalizedId.includes(normalizedActive)),
  };
}

function prepareEpisode(episode) {
  const metricRows = (episode?.metric_rows || [])
    .map((metric) => ({
      ...metric,
      key: metricKey(metric),
      group: metricGroup(metric.metric_name),
    }))
    .sort(compareMetricRows);

  const corePresent = new Set(
    metricRows
      .filter((metric) => metric.group === "core" && CORE_METRICS.includes(metric.metric_name))
      .map((metric) => metric.metric_name),
  );

  const groupCounts = {
    core: metricRows.filter((metric) => metric.group === "core").length,
    subgroups: metricRows.filter((metric) => metric.group === "subgroups").length,
    casualties: metricRows.filter((metric) => metric.group === "casualties").length,
    audit: metricRows.filter((metric) => metric.group === "audit").length,
  };

  return {
    ...episode,
    metric_rows: metricRows,
    group_counts: groupCounts,
    core_coverage: {
      present: corePresent.size,
      total: CORE_METRICS.length,
      percent: coveragePercent(corePresent.size, CORE_METRICS.length),
    },
    missing_core: CORE_METRICS.filter((metricName) => !corePresent.has(metricName)),
    source_count: episode?.source_count ?? (episode?.source_ledger || []).length,
  };
}

function normalize(value) {
  return String(value || "")
    .trim()
    .toLowerCase();
}
