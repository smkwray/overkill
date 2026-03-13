import {
  GROUP_META,
  attr,
  bestPosition,
  compactList,
  coveragePercent,
  escapeHtml,
  formatDateRange,
  formatMetricNumber,
  formatMetricRange,
  formatPrimaryMetricValue,
  formatUpdatedAt,
  icon,
  isFiniteNumber,
  metricLabel,
  metricShortLabel,
  previewText,
  qualityTone,
  ratioLabel,
  safeUrl,
  sourceClaimsForMetric,
} from "./utils.js";
import { getAvailableDecades } from "./map.js";

function sortDescription(sort) {
  switch (sort) {
    case "dr-asc":
      return "Sorted by Relative Risk, lowest first. RR\u2009&lt;\u20091 means civilians died at higher rates than combatants; RR\u2009&gt;\u20091 means combatants died at higher rates.";
    case "dr-desc":
      return "Sorted by Relative Risk, highest first.";
    case "victim":
      return "Grouped by affected side (the population most affected), ordered by each side\u2019s average RR. Within each group, episodes are sorted by individual RR.";
    case "inflicting":
      return "Grouped by armed force (the primary military actor), ordered by each side\u2019s average RR. Within each group, episodes are sorted by individual RR.";
    case "excess":
      return "Sorted by excess civilian deaths\u2009\u2014\u2009the number of civilian deaths above what parity (RR\u2009=\u20091) would predict given military deaths and population exposure. Larger values indicate more civilian deaths than expected under equal-risk conditions.";
    case "type":
      return "Grouped by episode type (massacre, siege, air bombardment, etc.), ordered by each type\u2019s average RR. Within each type, episodes are sorted by individual RR.";
    case "name":
      return "Sorted alphabetically by episode or conflict name.";
    default:
      return "";
  }
}

export function renderApp(state) {
  if (state.loading) {
    return renderStateShell({
      title: "Loading research bundles…",
      body: "Reading static bundle data and building the explorer shell.",
      tone: "muted",
    });
  }

  if (state.error) {
    return renderStateShell({
      title: "Could not load bundle data",
      body: escapeHtml(state.error),
      tone: "danger",
      extra: `
        <p class="state-note">Expected a static JSON export at <code>../data/index/bundles.json</code> or a local fallback. No backend is required.</p>
        <button type="button" class="icon-button" data-action="retry-boot" style="margin-top:var(--space-4)">Retry</button>
      `,
    });
  }

  return `
    <header class="app-header">
      <div class="app-header__brand">Overkill</div>
      <nav class="tab-nav" aria-label="Main navigation">
        ${renderTabBar(state)}
      </nav>
      <div class="app-header__actions">
        <button class="theme-toggle" type="button" data-action="toggle-theme" aria-label="Toggle light/dark theme">
          <span class="theme-icon-light">${icon("sun", 16)}</span>
          <span class="theme-icon-dark">${icon("moon", 16)}</span>
        </button>
      </div>
    </header>
    <main class="app-content" id="main-content" tabindex="-1">
      <div class="tab-content-scroll">
        ${renderTabContent(state)}
      </div>
    </main>
  `;
}

function renderStateShell({ title, body, tone = "muted", extra = "" }) {
  return `
    <div class="boot-shell">
      <section class="state-card">
        ${tone !== "danger" ? '<div class="loading-spinner"></div>' : ""}
        <span class="state-badge state-badge--${tone}">${tone === "danger" ? "Error" : "Loading"}</span>
        <h1>${escapeHtml(title)}</h1>
        <p>${escapeHtml(body)}</p>
        ${extra}
      </section>
    </div>
  `;
}

function renderTabBar(state) {
  const tabs = [
    { id: "map", label: "Map", iconName: "globe" },
    { id: "chart", label: "Chart", iconName: "bar-chart" },
    { id: "conflicts", label: "Conflicts", iconName: "folder" },
    { id: "explorer", label: "Explorer", iconName: "file-text" },
  ];

  return tabs.map((tab) => `
    <button
      type="button"
      class="tab-nav__item ${state.activeTab === tab.id ? "is-active" : ""}"
      data-action="select-tab"
      data-tab="${attr(tab.id)}"
      aria-selected="${state.activeTab === tab.id ? "true" : "false"}"
    >
      ${icon(tab.iconName, 16)}
      <span>${escapeHtml(tab.label)}</span>
    </button>
  `).join("");
}

function renderTabContent(state) {
  switch (state.activeTab) {
    case "map":
      return renderMapTab(state);
    case "chart":
      return renderChartTab(state);
    case "explorer":
      return renderExplorerTab(state);
    case "conflicts":
    default:
      return renderConflictsTab(state);
  }
}

/* ── Chart Tab ── */

function renderChartTab(state) {
  const bundles = state.overview?.bundles || [];
  const chartMode = state.chartMode || "episode";

  // Count items for current mode
  let itemCount = 0;
  if (chartMode === "episode") {
    for (const b of bundles) {
      for (const ep of b.episodes || []) {
        if ((ep.metric_rows || []).some((m) => m.metric_name === "dr_v1_direct" && m.value_best != null)) {
          itemCount++;
        }
      }
    }
  } else {
    itemCount = bundles.filter(
      (b) => (b.episodes || []).some((ep) => (ep.metric_rows || []).some((m) => m.metric_name === "dr_v1_direct" && m.value_best != null)),
    ).length;
  }

  const unitLabel = chartMode === "episode" ? "episodes" : "conflicts";

  return `
    <div class="chart-tab fade-in">
      <div class="chart-tab__header">
        <div>
          <p class="eyebrow">Relative risk overview</p>
          <h2>${escapeHtml(String(itemCount))} ${escapeHtml(unitLabel)} with RR estimates</h2>
        </div>
        <div class="chart-tab__controls">
          <div class="chart-mode-toggle" role="radiogroup" aria-label="Chart grouping">
            <button type="button" class="filter-chip ${chartMode === "episode" ? "is-active" : ""}" data-action="set-chart-mode" data-mode="episode" aria-pressed="${chartMode === "episode"}">Episodes</button>
            <button type="button" class="filter-chip ${chartMode === "conflict" ? "is-active" : ""}" data-action="set-chart-mode" data-mode="conflict" aria-pressed="${chartMode === "conflict"}">Conflicts</button>
          </div>
          <select id="chart-sort" class="chart-sort-select sort-hint-pulse" data-role="chart-sort" aria-label="Sort order">
            <option value="dr-asc" ${state.chartSort === "dr-asc" ? "selected" : ""}>RR (low \u2192 high)</option>
            <option value="dr-desc" ${state.chartSort === "dr-desc" ? "selected" : ""}>RR (high \u2192 low)</option>
            <option value="victim" ${state.chartSort === "victim" ? "selected" : ""}>Affected side (avg RR)</option>
            <option value="inflicting" ${state.chartSort === "inflicting" ? "selected" : ""}>Armed force (avg RR)</option>
            <option value="excess" ${state.chartSort === "excess" ? "selected" : ""}>Excess civ. deaths</option>
            <option value="type" ${state.chartSort === "type" ? "selected" : ""}>Episode type (avg RR)</option>
            <option value="name" ${state.chartSort === "name" ? "selected" : ""}>Name</option>
          </select>
        </div>
      </div>
      <div class="chart-tab__legend">
        <span class="chart-legend-item chart-legend-item--civ">RR &lt; 1 &mdash; Civilians at higher risk</span>
        <span class="chart-legend-ref">RR = 1</span>
        <span class="chart-legend-item chart-legend-item--mil">RR &gt; 1 &mdash; Military at higher risk</span>
      </div>
      <p class="chart-sort-desc">${sortDescription(state.chartSort || "dr-asc")}</p>
      <div class="chart-container" data-role="chart-container" data-sort="${attr(state.chartSort || "dr-asc")}"></div>
    </div>
  `;
}

/* ── Map Tab ── */

function countRREpisodes(bundles) {
  let n = 0;
  for (const b of bundles || []) {
    for (const ep of b.episodes || []) {
      if ((ep.metric_rows || []).some((m) => m.metric_name === "dr_v1_direct" && m.value_best != null)) n++;
    }
  }
  return n;
}

function renderMapTab(state) {
  const decades = getAvailableDecades(state.overview?.bundles);
  const currentIdx = state.mapDecade ? decades.indexOf(state.mapDecade) + 1 : 1;
  const rrCount = countRREpisodes(state.overview?.bundles);

  return `
    <div class="map-tab fade-in">
      ${renderTimelineControls(decades, currentIdx, state, rrCount)}
      <div class="map-layout">
        <div class="map-panel">
          <div class="map-container" data-role="map-container"></div>
        </div>
        <div class="map-drawer">
          ${renderMapConflictList(state)}
        </div>
      </div>
    </div>
  `;
}

function renderTimelineControls(decades, currentIdx, state, rrCount) {
  if (!decades.length) {
    return `<div class="timeline-controls"><span class="timeline-label" data-role="decade-label">No date data available</span></div>`;
  }

  return `
    <div class="timeline-controls">
      <span class="timeline-hint">${rrCount} episodes with RR estimates</span>
      <input
        type="range"
        class="timeline-slider"
        data-role="map-slider"
        min="1"
        max="${decades.length}"
        value="${currentIdx}"
        step="1"
        aria-label="Select decade"
      />
      <span class="timeline-label" data-role="decade-label">${state.mapDecade ? `${state.mapDecade}s` : `${decades[0]}s`}</span>
    </div>
  `;
}

export function renderMapConflictList(state) {
  const decade = state.mapDecade;
  const bundles = state.overview?.bundles || [];
  if (!decade || !bundles.length) {
    return `<div class="map-conflict-list" data-role="map-conflict-list"></div>`;
  }

  const conflicts = getConflictsForDecade(bundles, decade);

  if (!conflicts.length) {
    return `
      <div class="map-conflict-list" data-role="map-conflict-list">
        <p class="map-conflict-list__empty">No conflicts with civilian death estimates in the ${decade}s.</p>
      </div>
    `;
  }

  return `
    <div class="map-conflict-list" data-role="map-conflict-list">
      <h3 class="map-conflict-list__title">Conflicts in the ${escapeHtml(String(decade))}s</h3>
      <div class="map-conflict-grid">
        ${conflicts.map((c) => `
          <button
            type="button"
            class="map-conflict-item"
            data-action="select-bundle"
            data-bundle-id="${attr(c.bundle_id)}"
          >
            <div class="map-conflict-item__head">
              <strong>${escapeHtml(c.conflict_name || c.bundle_id)}</strong>
              ${c.civDeaths > 0 ? `<span class="map-conflict-item__deaths">${formatMapNumber(c.civDeaths)}</span>` : ""}
            </div>
            <span class="map-conflict-item__meta">${escapeHtml(c.dateRange)}${c.countries.length ? " · " + escapeHtml(c.countries.join(", ")) : ""}</span>
          </button>
        `).join("")}
      </div>
    </div>
  `;
}

function getConflictsForDecade(bundles, decade) {
  const results = [];
  for (const bundle of bundles) {
    let hasEpisodeInDecade = false;
    let civDeaths = 0;
    const countries = new Set();

    for (const episode of bundle.episodes || []) {
      const date = episode.start_date || bundle.start_date;
      const year = date ? new Date(date).getFullYear() : null;
      if (year && Math.floor(year / 10) * 10 === decade) {
        hasEpisodeInDecade = true;
        for (const metric of episode.metric_rows || []) {
          if (metric.metric_name === "civ_deaths_direct") {
            civDeaths += Number(metric.value_best) || 0;
          }
        }
        for (const c of episode.countries || []) countries.add(c);
      }
    }

    // Also check bundle-level date
    if (!hasEpisodeInDecade) {
      const year = bundle.start_date ? new Date(bundle.start_date).getFullYear() : null;
      if (year && Math.floor(year / 10) * 10 === decade) {
        hasEpisodeInDecade = true;
      }
    }

    if (hasEpisodeInDecade) {
      results.push({
        bundle_id: bundle.bundle_id,
        conflict_name: bundle.conflict_name,
        civDeaths,
        countries: [...countries],
        dateRange: formatDateRange(bundle.start_date, bundle.end_date),
      });
    }
  }
  return results.sort((a, b) => b.civDeaths - a.civDeaths);
}

function formatMapNumber(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return new Intl.NumberFormat().format(n);
}

/* ── Conflicts Tab ── */

function renderConflictsTab(state) {
  const bundles = state.visibleBundles || [];
  const total = state.overview?.bundles?.length || 0;
  const valid = state.overview?.valid_bundle_count ?? bundles.length;

  return `
    <div class="conflicts-tab fade-in">
      <div class="conflicts-tab__header">
        <div class="conflicts-tab__summary">
          <div class="summary-pill">
            <span class="summary-label">Bundles</span>
            <strong>${escapeHtml(String(total))}</strong>
          </div>
          <div class="summary-pill">
            <span class="summary-label">Valid</span>
            <strong>${escapeHtml(String(valid))}</strong>
          </div>
          <div class="summary-pill">
            <span class="summary-label">Updated</span>
            <strong>${escapeHtml(formatUpdatedAt(state.overview?.generated_at))}</strong>
          </div>
        </div>
        ${renderActiveTarget(state.overview?.active_target)}
        <div class="conflicts-tab__search">
          <label class="field-label" for="bundle-search">Find a conflict</label>
          <div class="search-wrapper">
            <span class="search-icon">${icon("search", 16)}</span>
            <input
              id="bundle-search"
              class="search-field"
              type="search"
              data-role="bundle-search"
              placeholder="Search bundle, country, region, alias"
              value="${attr(state.search || "")}"
              autocomplete="off"
            />
            ${state.search ? `<button class="search-clear" type="button" data-action="reset-browser-filter" aria-label="Clear search">${icon("x", 14)}</button>` : ""}
          </div>
          <div class="chip-row" role="toolbar" aria-label="Bundle filters">
            ${renderFilterChip(state.browserFilter, "all", "All")}
            ${renderFilterChip(state.browserFilter, "side", "Side")}
            ${renderFilterChip(state.browserFilter, "subgroups", "Subgroups")}
            ${renderFilterChip(state.browserFilter, "casualties", "Casualties")}
          </div>
          <span class="search-count" aria-live="polite">Showing ${escapeHtml(String(bundles.length))} of ${escapeHtml(String(total))}</span>
        </div>
      </div>
      ${
        bundles.length
          ? `<div class="conflicts-tab__grid">${bundles.map((bundle) => renderBundleCard(bundle, state)).join("")}</div>`
          : `
            <div class="empty-card">
              <span class="empty-icon">${icon("folder", 32)}</span>
              <strong>No bundles match this filter.</strong>
              <p>Clear the filter or broaden the search to bring conflicts back into view.</p>
              <button type="button" class="text-button" data-action="reset-browser-filter">${icon("x", 14)} Clear filters</button>
            </div>
          `
      }
    </div>
  `;
}

function renderActiveTarget(activeTarget) {
  if (!activeTarget) return "";
  return `
    <article class="target-card">
      <div class="section-bar section-bar--tight">
        <div>
          <p class="eyebrow">Active target</p>
          <strong>${escapeHtml(activeTarget.conflict_name || "Working target")}</strong>
        </div>
        ${activeTarget.date_range ? `<span class="state-badge state-badge--accent">${escapeHtml(activeTarget.date_range)}</span>` : ""}
      </div>
      ${activeTarget.focus ? `<p>${escapeHtml(previewText(activeTarget.focus))}</p>` : ""}
      ${activeTarget.note ? `<p class="muted-text">${escapeHtml(previewText(activeTarget.note))}</p>` : ""}
    </article>
  `;
}

function renderFilterChip(current, value, label) {
  return `
    <button
      type="button"
      class="filter-chip ${current === value ? "is-active" : ""}"
      data-action="set-browser-filter"
      data-filter="${attr(value)}"
      aria-pressed="${current === value ? "true" : "false"}"
    >
      ${escapeHtml(label)}
    </button>
  `;
}

function renderBundleCard(bundle, state) {
  const active = state.selectedBundle?.bundle_id === bundle.bundle_id;
  const coverage = bundle.estimated_ratio ?? coveragePercent(bundle.estimated_episode_count || 0, bundle.counts?.episodes || 0);

  return `
    <button
      type="button"
      class="bundle-card ${active ? "is-active" : ""}"
      data-action="select-bundle"
      data-bundle-id="${attr(bundle.bundle_id)}"
      aria-pressed="${active ? "true" : "false"}"
    >
      <div class="bundle-topline">
        <span class="bundle-id">${escapeHtml(bundle.bundle_id)}</span>
        ${bundle.quality_band ? `<span class="state-badge state-badge--${qualityTone(bundle.quality_band[0])}">Tier ${escapeHtml(bundle.quality_band)}</span>` : ""}
      </div>
      <h3>${escapeHtml(bundle.conflict_name || bundle.bundle_id)}</h3>
      <p class="bundle-meta">${escapeHtml(formatDateRange(bundle.start_date, bundle.end_date))}</p>
      <p class="bundle-meta">${escapeHtml(compactList(bundle.countries || []) || compactList(bundle.regions || []) || "Region not specified")}</p>
      <p class="bundle-note">${escapeHtml(previewText(bundle.notes, "No bundle note in export."))}</p>
      <div class="progress-track" aria-hidden="true">
        <span style="width:${coverage}%"></span>
      </div>
      <div class="bundle-footer">
        <span>${escapeHtml(String(bundle.estimated_episode_count || 0))}/${escapeHtml(String(bundle.counts?.episodes || 0))} estimated</span>
        <span>RR ${escapeHtml(ratioLabel(bundle.dr_range_best_values))}</span>
      </div>
    </button>
  `;
}

/* ── Explorer Tab ── */

function renderExplorerTab(state) {
  return `<div class="explorer-tab fade-in">${renderWorkspace(state)}</div>`;
}

function renderBreadcrumb(state) {
  const bundle = state.selectedBundle;
  const episode = state.selectedEpisode;
  const metric = state.selectedMetric;
  const crumbs = [];

  crumbs.push(`<li><button data-action="select-tab" data-tab="conflicts">All conflicts</button></li>`);

  if (bundle) {
    const name = escapeHtml(bundle.conflict_name || bundle.bundle_id);
    if (episode || metric) {
      crumbs.push(`<li><button data-action="select-bundle" data-bundle-id="${attr(bundle.bundle_id)}">${name}</button></li>`);
    } else {
      crumbs.push(`<li aria-current="page">${name}</li>`);
    }
  }

  if (episode) {
    const name = escapeHtml(episode.episode_name || episode.episode_id);
    if (metric) {
      crumbs.push(`<li><button data-action="select-episode" data-episode-id="${attr(episode.episode_id)}">${name}</button></li>`);
    } else {
      crumbs.push(`<li aria-current="page">${name}</li>`);
    }
  }

  if (metric) {
    crumbs.push(`<li aria-current="page">${escapeHtml(metricLabel(metric.metric_name))}</li>`);
  }

  return `<nav class="breadcrumb" aria-label="Navigation"><ol>${crumbs.join("")}</ol></nav>`;
}

function renderWorkspace(state) {
  const bundle = state.selectedBundle;
  const episode = state.selectedEpisode;

  if (!bundle) {
    return `
      <div class="workspace-shell fade-in">
        <header class="topbar">
          <div class="topbar-copy">
            <p class="eyebrow">Explorer</p>
            <h1>Select a conflict</h1>
          </div>
        </header>
        <section class="empty-panel">
          <span class="empty-icon">${icon("folder", 40)}</span>
          <h2>No bundle selected</h2>
          <p>Choose a conflict from the Conflicts tab to inspect episodes, metrics, and evidence.</p>
        </section>
      </div>
    `;
  }

  return `
    <div class="workspace-shell fade-in">
      <header class="topbar">
        <div class="topbar-copy">
          <p class="eyebrow">Conflict dossier</p>
          <h1>${escapeHtml(bundle.conflict_name || bundle.bundle_id)}</h1>
        </div>
      </header>
      ${renderBreadcrumb(state)}

      <section class="hero-card">
        <div class="hero-copy">
          <div class="section-bar">
            <div>
              <p class="eyebrow">Conflict summary</p>
              <h2>${escapeHtml(bundle.conflict_name || bundle.bundle_id)}</h2>
            </div>
            <div class="hero-badges">
              ${bundle.quality_band ? `<span class="state-badge state-badge--${qualityTone(bundle.quality_band[0])}">Tier ${escapeHtml(bundle.quality_band)}</span>` : ""}
              <span class="state-badge state-badge--muted">${escapeHtml(bundle.bundle_id)}</span>
            </div>
          </div>
          <p class="hero-note">${escapeHtml(previewText(bundle.notes, "No conflict summary in export."))}</p>
        </div>
        <div class="hero-stats">
          ${renderStat("Date range", formatDateRange(bundle.start_date, bundle.end_date))}
          ${renderStat("Countries", compactList(bundle.countries || []) || "Not specified")}
          ${renderStat("Episodes", `${bundle.estimated_episode_count || 0}/${bundle.counts?.episodes || 0} estimated`)}
          ${renderStat("Best RR span", ratioLabel(bundle.dr_range_best_values))}
        </div>
      </section>

      <section class="episode-section">
        <div class="section-bar">
          <div>
            <p class="eyebrow">Episode navigator</p>
            <h2>${escapeHtml(String((bundle.episodes || []).length))} episodes</h2>
          </div>
          ${episode?.quality_tier ? `<span class="state-badge state-badge--${qualityTone(episode.quality_tier)}">Episode ${escapeHtml(episode.quality_tier)}</span>` : ""}
        </div>
        <div class="episode-strip" role="tablist" aria-label="Episode selector">
          ${(bundle.episodes || []).map((entry) => renderEpisodeButton(entry, state)).join("")}
        </div>
      </section>

      ${episode ? renderEpisodeWorkspace(state) : renderEpisodeEmpty()}
    </div>
  `;
}

function renderStat(label, value) {
  return `
    <div class="stat-card">
      <span class="stat-label">${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `;
}

function renderEpisodeButton(episode, state) {
  const active = state.selectedEpisode?.episode_id === episode.episode_id;
  return `
    <button
      type="button"
      class="episode-pill ${active ? "is-active" : ""}"
      data-action="select-episode"
      data-episode-id="${attr(episode.episode_id)}"
      role="tab"
      aria-selected="${active ? "true" : "false"}"
    >
      <span class="episode-pill__name">${escapeHtml(episode.episode_name || episode.episode_id)}</span>
      <span class="episode-pill__meta">${escapeHtml(formatDateRange(episode.start_date, episode.end_date))}</span>
    </button>
  `;
}

function renderEpisodeWorkspace(state) {
  const episode = state.selectedEpisode;
  return `
    <section class="episode-header-card">
      <div class="section-bar">
        <div>
          <p class="eyebrow">Episode focus</p>
          <h2>${escapeHtml(episode.episode_name || episode.episode_id)}</h2>
        </div>
        <div class="hero-badges">
          ${episode.quality_tier ? `<span class="state-badge state-badge--${qualityTone(episode.quality_tier)}">Tier ${escapeHtml(episode.quality_tier)}</span>` : ""}
          <span class="state-badge state-badge--muted">${escapeHtml(episode.geographic_scope || "Scope unknown")}</span>
        </div>
      </div>
      <p class="hero-note">${escapeHtml(previewText(episode.theater_description, "No theater description in export."))}</p>
      <div class="episode-inline-meta">
        ${renderMetaItem("Dates", formatDateRange(episode.start_date, episode.end_date))}
        ${renderMetaItem("Open questions", String(episode.open_question_count ?? 0))}
        ${renderMetaItem("Sources", String(episode.source_count ?? 0))}
        ${renderMetaItem("Claims", String(episode.claim_count ?? 0))}
      </div>
    </section>

    <section class="metrics-section panel-card">
      <div class="section-bar">
        <div class="section-bar__left">
          <h3>${escapeHtml(GROUP_META[state.activeLayer]?.label || "Metrics")} (${escapeHtml(String((state.layerTiles || []).length))})</h3>
          ${renderLayerTabs(state)}
        </div>
      </div>
      ${renderMetricTable(state)}
    </section>

    <section class="workspace-grid">
      <div class="detail-column panel-card">
        ${renderMetricDetail(state)}
      </div>
    </section>

    <section class="evidence-panel panel-card">
      ${renderEvidenceSection(state)}
    </section>
  `;
}

function renderEpisodeEmpty() {
  return `
    <section class="empty-panel">
      <span class="empty-icon">${icon("clock", 36)}</span>
      <h2>No episode selected</h2>
      <p>Choose an episode above to inspect its metrics and sources.</p>
    </section>
  `;
}

function renderMetaItem(label, value) {
  return `
    <div class="meta-item">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `;
}

function renderLayerTabs(state) {
  return `
    <div class="tab-row tab-row--inline" role="tablist" aria-label="Metric layers">
      ${state.availableGroups
        .map(
          (group) => `
            <button
              type="button"
              class="tab-button ${state.activeLayer === group ? "is-active" : ""}"
              data-action="select-layer"
              data-layer="${attr(group)}"
              role="tab"
              aria-selected="${state.activeLayer === group ? "true" : "false"}"
            >
              ${escapeHtml(GROUP_META[group]?.label || group)}
            </button>
          `,
        )
        .join("")}
    </div>
  `;
}

/* ── Metric Table ── */

function renderMetricTable(state) {
  const metrics = state.layerTiles || [];
  if (!metrics.length) {
    return `
      <div class="empty-card">
        <strong>No ${escapeHtml(state.activeLayer)} metrics in this episode.</strong>
        <p>This layer is empty in the current export.</p>
      </div>
    `;
  }

  // Compute global min/max for sparkline normalization
  const numericMetrics = metrics.filter((m) => !m.__missing);
  let globalMin = Infinity;
  let globalMax = -Infinity;
  for (const m of numericMetrics) {
    const low = isFiniteNumber(m.value_low) ? Number(m.value_low) : null;
    const high = isFiniteNumber(m.value_high) ? Number(m.value_high) : null;
    const best = isFiniteNumber(m.value_best) ? Number(m.value_best) : null;
    const vals = [low, high, best].filter((v) => v !== null);
    for (const v of vals) {
      if (v < globalMin) globalMin = v;
      if (v > globalMax) globalMax = v;
    }
  }
  if (!isFinite(globalMin)) globalMin = 0;
  if (!isFinite(globalMax)) globalMax = 1;
  if (globalMax === globalMin) globalMax = globalMin + 1;

  return `
    <div class="metric-table-wrap">
      <table class="metric-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>Best</th>
            <th class="metric-table__range-col">Range</th>
            <th>Tier</th>
            <th>Src</th>
          </tr>
        </thead>
        <tbody>
          ${metrics.map((m) => renderMetricRow(m, state, globalMin, globalMax)).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderMetricRow(metric, state, globalMin, globalMax) {
  if (metric.__missing) {
    return `
      <tr class="metric-row metric-row--missing">
        <td class="metric-name">${escapeHtml(metricLabel(metric.metric_name))}</td>
        <td class="metric-best">—</td>
        <td class="metric-table__range-col"><span class="muted">Missing</span></td>
        <td>—</td>
        <td>—</td>
      </tr>
    `;
  }

  const active = state.selectedMetric?.key === metric.key;

  return `
    <tr
      class="metric-row ${active ? "is-active" : ""}"
      data-action="select-metric"
      data-metric-key="${attr(metric.key)}"
      tabindex="0"
      role="button"
    >
      <td class="metric-name">
        ${escapeHtml(metricShortLabel(metric.metric_name))}
        ${metric.victim_side ? `<span class="metric-side-hint">${escapeHtml(metric.victim_side)}</span>` : ""}
      </td>
      <td class="metric-best">${escapeHtml(formatPrimaryMetricValue(metric))}</td>
      <td class="metric-table__range-col">${renderSparkline(metric, globalMin, globalMax)}</td>
      <td>${metric.quality_tier ? `<span class="tier-badge tier-badge--${qualityTone(metric.quality_tier)}">${escapeHtml(metric.quality_tier)}</span>` : "—"}</td>
      <td class="metric-src-count">${escapeHtml(String(metric.source_refs?.length || 0))}</td>
    </tr>
  `;
}

function renderSparkline(metric, globalMin, globalMax) {
  const low = isFiniteNumber(metric.value_low) ? Number(metric.value_low) : null;
  const high = isFiniteNumber(metric.value_high) ? Number(metric.value_high) : null;
  const best = isFiniteNumber(metric.value_best) ? Number(metric.value_best) : null;

  const range = globalMax - globalMin;
  const pctLow = low !== null ? Math.max(0, ((low - globalMin) / range) * 100) : 0;
  const pctHigh = high !== null ? Math.min(100, ((high - globalMin) / range) * 100) : 100;
  const pctBest = best !== null ? Math.max(0, Math.min(100, ((best - globalMin) / range) * 100)) : null;

  const lowText = low !== null ? formatMetricNumber(low, metric.metric_name) : "";
  const highText = high !== null ? formatMetricNumber(high, metric.metric_name) : "";

  return `
    <div class="spark-track">
      <span class="spark-range" style="left:${pctLow.toFixed(1)}%;width:${Math.max(0, pctHigh - pctLow).toFixed(1)}%"></span>
      ${pctBest !== null ? `<span class="spark-marker" style="left:${pctBest.toFixed(1)}%"></span>` : ""}
    </div>
    <span class="spark-label">${lowText}${lowText && highText ? " – " : ""}${highText}</span>
  `;
}

/* ── Metric Detail ── */

function renderMetricDetail(state) {
  const metric = state.selectedMetric;
  const episode = state.selectedEpisode;

  if (!metric) {
    return `
      <div class="detail-shell">
        <div class="section-bar">
          <div>
            <p class="eyebrow">Metric detail</p>
            <h3>Select a metric</h3>
          </div>
        </div>
        <div class="empty-card">
          <span class="empty-icon">${icon("bar-chart", 28)}</span>
          <p>Choose a metric row to inspect its uncertainty band, notes, and supporting sources.</p>
        </div>
      </div>
    `;
  }

  return `
    <div class="detail-shell">
      <div class="section-bar">
        <div>
          <p class="eyebrow">Metric detail</p>
          <h3>${escapeHtml(metricLabel(metric.metric_name))}</h3>
        </div>
        ${metric.quality_tier ? `<span class="state-badge state-badge--${qualityTone(metric.quality_tier)}">Tier ${escapeHtml(metric.quality_tier)}</span>` : ""}
      </div>

      <div class="detail-hero">
        <div>
          <span class="detail-value">${escapeHtml(formatPrimaryMetricValue(metric))}</span>
          <p class="detail-range">${escapeHtml(formatMetricRange(metric))}</p>
        </div>
        <div class="detail-band" aria-hidden="true">
          <span class="detail-band__track"></span>
          <span class="detail-band__fill"></span>
          <span class="detail-band__marker" style="left:${attr(bestPosition(metric))}"></span>
        </div>
      </div>

      <div class="detail-meta-grid">
        ${renderDetailFact("Unit", metric.unit || "Unknown")}
        ${renderDetailFact("Estimate method", metric.estimate_method || "Not stated")}
        ${renderDetailFact("Unknown rule", metric.unknown_status_rule || "Not stated")}
        ${renderDetailFact("Episode", episode?.episode_name || episode?.episode_id || "Unknown")}
      </div>

      <div class="detail-notes">
        ${renderNoteCard("Affected side", metric.victim_side || "Not specified")}
        ${renderNoteCard("Armed force", metric.inflicting_side || "Not specified")}
        ${metric.formula_note ? renderNoteCard("Formula", metric.formula_note) : ""}
        ${metric.uncertainty_note ? renderNoteCard("Uncertainty", metric.uncertainty_note) : ""}
        ${metric.quality_note ? renderNoteCard("Quality note", metric.quality_note) : ""}
      </div>

      <div class="detail-related">
        <div class="section-bar section-bar--tight">
          <div>
            <p class="eyebrow">Evidence links</p>
            <h4>Supporting sources</h4>
          </div>
          <span class="soft-count">${escapeHtml(String(metric.source_refs?.length || 0))}</span>
        </div>
        ${(metric.source_refs || []).length
          ? `<div class="source-chip-row">${metric.source_refs
              .map(
                (source) => `
                  <button
                    type="button"
                    class="source-chip"
                    data-action="select-source"
                    data-source-id="${attr(source.source_id)}"
                    data-source-scope="episode"
                  >
                    <span>${escapeHtml(source.citation_short || source.source_id)}</span>
                    <span class="muted-inline">${escapeHtml(source.source_type || "Source")}</span>
                  </button>
                `,
              )
              .join("")}</div>`
          : `<div class="empty-card"><p>No source references were attached to this metric row.</p></div>`}
      </div>
    </div>
  `;
}

function renderDetailFact(label, value) {
  return `
    <div class="detail-fact">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `;
}

function renderNoteCard(label, body) {
  return `
    <article class="note-card">
      <span class="note-card__label">${escapeHtml(label)}</span>
      <p>${escapeHtml(previewText(body, "No note."))}</p>
    </article>
  `;
}

/* ── Evidence Section ── */

function renderEvidenceSection(state) {
  const selectedMetric = state.selectedMetric;
  const activeSource = state.selectedSource || state.inspectorSources?.[0] || null;
  const claims = sourceClaimsForMetric(activeSource, selectedMetric);

  return `
    <section class="inspector-shell evidence-scroll">
      <div class="section-bar">
        <div>
          <p class="eyebrow">Episode evidence</p>
          <h2>Sources and claims</h2>
        </div>
        <span class="soft-count">${escapeHtml(String((state.inspectorSources || []).length))}</span>
      </div>

      <div class="inspector-caption">
        <span>Only episode-level evidence is shown here.</span>
        <strong>${state.selectedMetric ? escapeHtml(metricLabel(state.selectedMetric.metric_name)) : "Select a metric"}</strong>
      </div>

      ${
        (state.inspectorSources || []).length
          ? `<div class="inspector-list">${state.inspectorSources.map((source) => renderSourceListItem(source, activeSource)).join("")}</div>`
          : `<div class="empty-card"><p>No episode sources are attached to the current selection.</p></div>`
      }

      ${activeSource ? renderSourceDetail(activeSource, claims, state) : '<div class="empty-card"><p>Select a metric or source chip to inspect evidence.</p></div>'}
    </section>
  `;
}

function renderSourceListItem(source, activeSource) {
  const active = activeSource?.source_id === source.source_id;
  return `
    <button
      type="button"
      class="source-list-item ${active ? "is-active" : ""}"
      data-action="select-source"
      data-source-id="${attr(source.source_id)}"
      aria-pressed="${active ? "true" : "false"}"
    >
      <div>
        <strong>${escapeHtml(source.citation_short || source.source_id)}</strong>
        <p>${escapeHtml(source.title || source.notes || "Untitled source")}</p>
      </div>
      <div class="source-list-meta">
        ${source.claim_count ? `<span>${escapeHtml(String(source.claim_count))} claims</span>` : ""}
        ${source.source_type ? `<span>${escapeHtml(source.source_type)}</span>` : ""}
      </div>
    </button>
  `;
}

function renderSourceDetail(source, claims, state) {
  const url = safeUrl(source.url);
  return `
    <article class="source-detail">
      <div class="section-bar section-bar--tight">
        <div>
          <p class="eyebrow">Selected source</p>
          <h3>${escapeHtml(source.citation_short || source.source_id)}</h3>
        </div>
        ${source.source_type ? `<span class="state-badge state-badge--muted">${escapeHtml(source.source_type)}</span>` : ""}
      </div>

      <div class="source-detail__meta">
        ${source.title ? renderDetailFact("Title", source.title) : ""}
        ${source.author_or_org ? renderDetailFact("Author / org", source.author_or_org) : ""}
        ${source.pages_or_sections ? renderDetailFact("Pages / sections", source.pages_or_sections) : ""}
        ${source.geographic_scope ? renderDetailFact("Geography", source.geographic_scope) : ""}
      </div>

      ${source.strengths ? renderNoteCard("Strengths", source.strengths) : ""}
      ${source.limitations ? renderNoteCard("Limitations", source.limitations) : ""}
      ${source.notes ? renderNoteCard("Notes", source.notes) : ""}

      ${
        url
          ? `<p><a class="source-link" href="${attr(url)}" target="_blank" rel="noreferrer">Open source ${icon("external-link", 14)}</a></p>`
          : ""
      }

      <div class="claims-block">
        <div class="section-bar section-bar--tight">
          <div>
            <p class="eyebrow">Claim excerpts</p>
            <h4>${escapeHtml(String(claims.length))} linked claims</h4>
          </div>
          ${state.selectedMetric ? `<span class="soft-count">${escapeHtml(metricLabel(state.selectedMetric.metric_name))}</span>` : ""}
        </div>
        ${
          claims.length
            ? claims.map(renderClaimCard).join("")
            : `<div class="empty-card"><p>No linked claim excerpts for the current metric.</p></div>`
        }
      </div>
    </article>
  `;
}

function renderClaimCard(claim) {
  return `
    <article class="claim-card">
      <div class="claim-card__top">
        <strong>${escapeHtml(claim.variable_name || claim.claim_id || "Claim")}</strong>
        ${claim.pages_or_sections ? `<span>${escapeHtml(claim.pages_or_sections)}</span>` : ""}
      </div>
      ${
        claim.excerpt
          ? `<p>${escapeHtml(previewText(claim.excerpt, "No excerpt provided."))}</p>`
          : claim.claim_text
            ? `<p>${escapeHtml(previewText(claim.claim_text, "No excerpt provided."))}</p>`
            : `<p>No excerpt provided.</p>`
      }
      ${
        claim.value_best !== undefined || claim.best !== undefined
          ? `<div class="claim-values">${escapeHtml(renderClaimValueRange(claim))}</div>`
          : ""
      }
    </article>
  `;
}

function renderClaimValueRange(claim) {
  const low = claim.value_low ?? claim.low;
  const best = claim.value_best ?? claim.best;
  const high = claim.value_high ?? claim.high;
  const metricName = claim.variable_name || claim.metric || "value";

  if (low == null && best == null && high == null) return "";
  if (low != null && high != null && best != null) {
    return `${formatMetricNumber(low, metricName)} – ${formatMetricNumber(high, metricName)} · best ${formatMetricNumber(best, metricName)}`;
  }
  if (best != null) return `Best ${formatMetricNumber(best, metricName)}`;
  if (low != null && high != null) return `${formatMetricNumber(low, metricName)} – ${formatMetricNumber(high, metricName)}`;
  return formatMetricNumber(low ?? high, metricName);
}
