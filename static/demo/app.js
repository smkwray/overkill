import { loadOverview, prepareOverview } from "./js/data.js";
import { buildRoute, readRoute, sameRoute } from "./js/router.js";
import { renderApp, renderMapConflictList } from "./js/render.js";
import { initMap, updateMapDecade, refreshMapTheme, getAvailableDecades } from "./js/map.js";
import { initDRChart } from "./js/chart.js";
import {
  availableGroups,
  buildLayerTiles,
  defaultBundle,
  defaultEpisode,
  defaultMetricForGroup,
  findMetricByKey,
  sortSourcesForMetric,
} from "./js/utils.js";

const root = document.getElementById("app");
const DEFAULT_TAB = "chart";

let mapAutoplayTimer = null;
let mapAutoplayRestart = null;

const state = {
  loading: true,
  error: "",
  overview: null,

  activeTab: DEFAULT_TAB,
  mapDecade: null,

  search: "",
  browserFilter: "all",

  selectedBundleId: null,
  selectedEpisodeId: null,
  selectedMetricKey: null,
  selectedSourceId: null,

  activeLayer: "core",
  chartSort: "dr-asc",
  chartMode: "episode",

  visibleBundles: [],
  selectedBundle: null,
  selectedEpisode: null,
  selectedMetric: null,
  selectedSource: null,
  layerTiles: [],
  inspectorSources: [],
  availableGroups: ["core"],
};

let pendingRenderIntent = null;

/* ── Theme toggle ── */

function initTheme() {
  const stored = localStorage.getItem("overkill-theme");
  if (stored === "light" || stored === "dark") {
    document.documentElement.dataset.theme = stored;
  }
}

function toggleTheme() {
  const current = document.documentElement.dataset.theme;
  const isCurrentlyLight =
    current === "light" ||
    (!current && window.matchMedia("(prefers-color-scheme: light)").matches);
  const next = isCurrentlyLight ? "dark" : "light";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("overkill-theme", next);
  refreshMapTheme();
}

initTheme();
boot();

async function boot() {
  try {
    render();

    const raw = await loadOverview();
    state.overview = prepareOverview(raw);
    state.loading = false;

    // Default mapDecade to first available decade (no "all time")
    const decades = getAvailableDecades(state.overview?.bundles);
    if (decades.length && !state.mapDecade) {
      state.mapDecade = decades[0];
    }

    applyRoute(readRoute());
    deriveState();
    replaceUrlFromState();
    render();
  } catch (error) {
    state.loading = false;
    state.error = error?.message || String(error);
    render();
  }
}

window.addEventListener("hashchange", () => {
  applyRoute(readRoute());
  deriveState();

  if (replaceUrlFromState()) {
    render(pendingRenderIntent || { resetMain: false, resetInspector: false });
  }

  pendingRenderIntent = null;
});

document.addEventListener("keydown", (event) => {
  // "/" to focus search (when not already in an input)
  if (event.key === "/" && !(event.target instanceof HTMLInputElement) && !(event.target instanceof HTMLTextAreaElement)) {
    event.preventDefault();
    // If not on conflicts tab, switch to it
    if (state.activeTab !== "conflicts") {
      state.activeTab = "conflicts";
      deriveState();
      navigateFromState();
    }
    requestAnimationFrame(() => {
      const searchInput = root.querySelector('[data-role="bundle-search"]');
      if (searchInput) searchInput.focus();
    });
  }
});

root.addEventListener("change", (event) => {
  const target = event.target;
  if (target instanceof HTMLSelectElement && target.dataset.role === "chart-sort") {
    state.chartSort = target.value;
    render();
  }
});

root.addEventListener("input", (event) => {
  const target = event.target;

  if (target instanceof HTMLInputElement && target.dataset.role === "bundle-search") {
    state.search = target.value;
    deriveState();
    render({ preserveSearchFocus: true });
  }

  if (target instanceof HTMLInputElement && target.dataset.role === "map-slider") {
    // User manually moved slider — pause autoplay
    stopMapAutoplay();
    const decades = getAvailableDecades(state.overview?.bundles);
    const idx = Number(target.value);
    state.mapDecade = decades[idx - 1] || decades[0] || null;
    updateMapDecade(state.mapDecade);
    // Update label without full re-render
    const label = root.querySelector('[data-role="decade-label"]');
    if (label) label.textContent = state.mapDecade ? `${state.mapDecade}s` : "";
    // Re-render the conflict list
    const listEl = root.querySelector('[data-role="map-conflict-list"]');
    if (listEl) {
      listEl.outerHTML = renderMapConflictList(state);
    }
    // Restart autoplay after 5s idle
    restartMapAutoplayAfterDelay();
  }
});

root.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-action]");
  if (!trigger) return;

  const action = trigger.dataset.action;

  switch (action) {
    case "select-tab": {
      const tab = trigger.dataset.tab;
      if (!tab || tab === state.activeTab) return;
      state.activeTab = tab;
      deriveState();
      navigateFromState();
      return;
    }

    case "reset-browser-filter": {
      state.search = "";
      state.browserFilter = "all";
      deriveState();
      render();
      return;
    }

    case "set-browser-filter": {
      const filter = trigger.dataset.filter || "all";
      state.browserFilter = filter;
      deriveState();
      render();
      return;
    }

    case "select-bundle": {
      const bundleId = trigger.dataset.bundleId;
      if (!bundleId) return;

      state.selectedBundleId = bundleId;
      state.selectedEpisodeId = null;
      state.selectedMetricKey = null;
      state.selectedSourceId = null;
      state.activeTab = "explorer";
      deriveState();

      pendingRenderIntent = { resetMain: true, resetInspector: false };
      navigateFromState();
      return;
    }

    case "select-episode": {
      const episodeId = trigger.dataset.episodeId;
      if (!episodeId) return;

      state.selectedEpisodeId = episodeId;
      state.selectedMetricKey = null;
      state.selectedSourceId = null;
      deriveState();

      pendingRenderIntent = { resetMain: false, resetInspector: false };
      navigateFromState();
      return;
    }

    case "select-layer": {
      const layer = trigger.dataset.layer || "core";
      state.activeLayer = layer;
      state.selectedMetricKey = null;
      state.selectedSourceId = null;
      deriveState();

      pendingRenderIntent = { resetMain: false, resetInspector: false };
      navigateFromState();
      return;
    }

    case "select-metric": {
      const metricKey = trigger.dataset.metricKey;
      if (!metricKey) return;

      state.selectedMetricKey = metricKey;
      state.selectedSourceId = null;
      deriveState();

      pendingRenderIntent = { resetMain: false, resetInspector: false };
      navigateFromState();
      return;
    }

    case "select-source": {
      const sourceId = trigger.dataset.sourceId;
      if (!sourceId) return;

      state.selectedSourceId = sourceId;
      deriveState();

      pendingRenderIntent = { resetMain: false, resetInspector: false };
      navigateFromState();
      return;
    }

    case "set-chart-mode": {
      const mode = trigger.dataset.mode || "episode";
      if (mode !== state.chartMode) {
        state.chartMode = mode;
        render();
      }
      return;
    }

    case "toggle-theme": {
      toggleTheme();
      return;
    }

    case "retry-boot": {
      state.loading = true;
      state.error = "";
      boot();
      return;
    }

    default:
      return;
  }
});


// Handle map country click — navigate to Explorer with the clicked bundle
root.addEventListener("map-country-click", (event) => {
  const bundleId = event.detail?.bundleId;
  if (!bundleId) return;

  state.selectedBundleId = bundleId;
  state.selectedEpisodeId = null;
  state.selectedMetricKey = null;
  state.selectedSourceId = null;
  state.activeTab = "explorer";
  deriveState();

  pendingRenderIntent = { resetMain: true, resetInspector: false };
  navigateFromState();
});

function deriveState() {
  const bundles = state.overview?.bundles || [];
  state.visibleBundles = bundles.filter(matchesBundleBrowserFilter);

  if (!bundles.length) {
    state.selectedBundle = null;
    state.selectedEpisode = null;
    state.selectedMetric = null;
    state.selectedSource = null;
    state.availableGroups = ["core"];
    state.layerTiles = [];
    state.inspectorSources = [];
    return;
  }

  if (!bundles.some((bundle) => bundle.bundle_id === state.selectedBundleId)) {
    state.selectedBundleId = state.overview?.default_bundle_id || defaultBundle(bundles)?.bundle_id || null;
  }

  state.selectedBundle = bundles.find((bundle) => bundle.bundle_id === state.selectedBundleId) || null;

  const bundle = state.selectedBundle;
  const episodes = bundle?.episodes || [];

  if (!episodes.some((episode) => episode.episode_id === state.selectedEpisodeId)) {
    state.selectedEpisodeId = defaultEpisode(bundle)?.episode_id || null;
  }

  state.selectedEpisode = episodes.find((episode) => episode.episode_id === state.selectedEpisodeId) || null;

  const episode = state.selectedEpisode;
  const metrics = episode?.metric_rows || [];

  const routedMetric = findMetricByKey(metrics, state.selectedMetricKey);
  if (routedMetric) {
    state.activeLayer = routedMetric.group;
  }

  state.availableGroups = availableGroups(episode);

  if (!state.availableGroups.includes(state.activeLayer)) {
    state.activeLayer = state.availableGroups[0] || "core";
  }

  state.layerTiles = buildLayerTiles(episode, state.activeLayer);

  const currentMetric =
    metrics.find((metric) => metric.key === state.selectedMetricKey && metric.group === state.activeLayer) ||
    null;

  if (!currentMetric) {
    state.selectedMetricKey = defaultMetricForGroup(episode, state.activeLayer)?.key || null;
  }

  state.selectedMetric = findMetricByKey(metrics, state.selectedMetricKey);

  if (state.selectedMetric && state.selectedMetric.group !== state.activeLayer) {
    state.activeLayer = state.selectedMetric.group;
    state.layerTiles = buildLayerTiles(episode, state.activeLayer);
  }

  const rawSources = episode?.source_ledger || [];
  state.inspectorSources = sortSourcesForMetric(rawSources, state.selectedMetric);

  if (!state.inspectorSources.some((source) => source.source_id === state.selectedSourceId)) {
    state.selectedSourceId = null;
  }

  state.selectedSource =
    state.inspectorSources.find((source) => source.source_id === state.selectedSourceId) || null;
}

function matchesBundleBrowserFilter(bundle) {
  const query = normalize(state.search);
  const filter = state.browserFilter;

  const searchMatches = !query || [
    bundle.bundle_id,
    bundle.conflict_id,
    bundle.conflict_name,
    ...(bundle.aliases || []),
    ...(bundle.countries || []),
    ...(bundle.regions || []),
  ].some((value) => normalize(value).includes(query));

  if (!searchMatches) return false;

  switch (filter) {
    case "side":
      return Boolean(bundle.features?.hasSideMetrics);
    case "subgroups":
      return Boolean(bundle.features?.hasSubgroups);
    case "casualties":
      return Boolean(bundle.features?.hasCasualties);
    default:
      return true;
  }
}

function applyRoute(route) {
  state.activeTab = route.tab || DEFAULT_TAB;
  state.selectedBundleId = route.bundle || state.selectedBundleId;
  state.selectedEpisodeId = route.episode || null;
  state.selectedMetricKey = route.metric || null;
  state.selectedSourceId = route.source || null;
  state.activeLayer = route.layer || "core";
}

function routeFromState() {
  return {
    tab: state.activeTab,
    bundle: state.selectedBundleId,
    episode: state.selectedEpisodeId,
    metric: state.selectedMetricKey,
    source: state.selectedSourceId,
    scope: "episode",
    layer: state.activeLayer,
  };
}

function navigateFromState() {
  const nextRoute = routeFromState();
  if (sameRoute(nextRoute)) {
    render(pendingRenderIntent || {});
    pendingRenderIntent = null;
    return;
  }

  window.location.hash = buildRoute(nextRoute);
}

function replaceUrlFromState() {
  const nextHash = buildRoute(routeFromState());
  if ((window.location.hash || "#") === nextHash) {
    return true;
  }

  history.replaceState(null, "", nextHash);
  return true;
}

function render(intent = {}) {
  const preserveSearchFocus = Boolean(intent.preserveSearchFocus);
  const previousSearch = preserveSearchFocus ? snapshotSearchFocus() : null;
  const scrollPositions = snapshotScrollPositions();

  root.innerHTML = renderApp(state);
  updatePageTitle();

  restoreScrollPositions(scrollPositions, intent);

  if (previousSearch) {
    restoreSearchFocus(previousSearch);
  }

  // Scroll active items into view on navigation
  if (intent.resetMain) {
    requestAnimationFrame(() => {
      const activeBundle = root.querySelector(".bundle-card.is-active");
      if (activeBundle) activeBundle.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }

  // Post-render: init map if on map tab
  if (state.activeTab === "map" && !state.loading && !state.error) {
    const container = root.querySelector('[data-role="map-container"]');
    if (container) {
      initMap(container, state.overview, state.mapDecade);
    }
    startMapAutoplay();
    // Subtle pulse on the Chart tab to draw attention
    const chartTab = root.querySelector('[data-tab="chart"]');
    if (chartTab) chartTab.classList.add("tab-hint-pulse");
  } else {
    stopMapAutoplay();
  }

  // Post-render: init chart if on chart tab
  if (state.activeTab === "chart" && !state.loading && !state.error) {
    const chartContainer = root.querySelector('[data-role="chart-container"]');
    if (chartContainer) {
      initDRChart(chartContainer, state.overview?.bundles, {
        mode: state.chartMode || "episode",
        onBarClick: (bundleId, episodeId) => {
          state.selectedBundleId = bundleId;
          state.selectedEpisodeId = episodeId || null;
          state.selectedMetricKey = null;
          state.selectedSourceId = null;
          state.activeTab = "explorer";
          deriveState();
          pendingRenderIntent = { resetMain: true, resetInspector: false };
          navigateFromState();
        },
      });
    }
  }
}

function snapshotSearchFocus() {
  const active = document.activeElement;
  if (!(active instanceof HTMLInputElement) || active.dataset.role !== "bundle-search") {
    return null;
  }

  return {
    start: active.selectionStart,
    end: active.selectionEnd,
  };
}

function restoreSearchFocus(snapshot) {
  const input = root.querySelector('[data-role="bundle-search"]');
  if (!(input instanceof HTMLInputElement)) return;
  input.focus();
  if (snapshot?.start !== null && snapshot?.start !== undefined) {
    input.setSelectionRange(snapshot.start, snapshot.end ?? snapshot.start);
  }
}

function snapshotScrollPositions() {
  return {
    tabContent: root.querySelector(".tab-content-scroll")?.scrollTop ?? 0,
    main: root.querySelector(".main-scroll")?.scrollTop ?? 0,
    inspector: root.querySelector(".evidence-scroll")?.scrollTop ?? 0,
    episodeStrip: root.querySelector(".episode-strip")?.scrollLeft ?? 0,
  };
}

function restoreScrollPositions(previous, intent) {
  const tabContent = root.querySelector(".tab-content-scroll");
  const main = root.querySelector(".main-scroll");
  const inspector = root.querySelector(".evidence-scroll");
  const episodeStrip = root.querySelector(".episode-strip");

  if (tabContent) tabContent.scrollTop = intent.resetMain ? 0 : (previous.tabContent ?? 0);
  if (main) main.scrollTop = intent.resetMain ? 0 : (previous.main ?? 0);
  if (inspector) inspector.scrollTop = intent.resetInspector ? 0 : (previous.inspector ?? 0);
  if (episodeStrip) episodeStrip.scrollLeft = previous.episodeStrip ?? 0;
}

function updatePageTitle() {
  const tabNames = { map: "Map", conflicts: "Conflicts", chart: "Chart", explorer: "Explorer" };
  const parts = [];

  if (state.activeTab === "explorer") {
    if (state.selectedBundle) {
      parts.push(state.selectedBundle.conflict_name || state.selectedBundle.bundle_id);
    }
    if (state.selectedEpisode) {
      parts.push(state.selectedEpisode.episode_name || state.selectedEpisode.episode_id);
    }
  }

  const tabLabel = tabNames[state.activeTab] || "Conflicts";

  if (parts.length) {
    document.title = `${parts.join(" — ")} — Overkill`;
  } else {
    document.title = `${tabLabel} — Overkill`;
  }
}

function normalize(value) {
  return String(value || "")
    .trim()
    .toLowerCase();
}

/* ── Map autoplay ── */

function startMapAutoplay() {
  stopMapAutoplay();
  mapAutoplayTimer = setInterval(() => {
    const decades = getAvailableDecades(state.overview?.bundles);
    if (!decades.length) return;
    const curIdx = decades.indexOf(state.mapDecade);
    const nextIdx = (curIdx + 1) % decades.length;
    state.mapDecade = decades[nextIdx];
    updateMapDecade(state.mapDecade);
    // Sync slider + label without full re-render
    const slider = root.querySelector('[data-role="map-slider"]');
    if (slider) slider.value = String(nextIdx + 1);
    const label = root.querySelector('[data-role="decade-label"]');
    if (label) label.textContent = `${state.mapDecade}s`;
    const listEl = root.querySelector('[data-role="map-conflict-list"]');
    if (listEl) listEl.outerHTML = renderMapConflictList(state);
  }, 3000);
}

function stopMapAutoplay() {
  if (mapAutoplayTimer) { clearInterval(mapAutoplayTimer); mapAutoplayTimer = null; }
  if (mapAutoplayRestart) { clearTimeout(mapAutoplayRestart); mapAutoplayRestart = null; }
}

function restartMapAutoplayAfterDelay() {
  if (mapAutoplayRestart) clearTimeout(mapAutoplayRestart);
  mapAutoplayRestart = setTimeout(() => { startMapAutoplay(); }, 5000);
}
