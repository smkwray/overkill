import { escapeHtml, formatMetricNumber } from "./utils.js";

const TYPE_LABELS = {
  massacre: "Massacre",
  siege: "Siege",
  uprising: "Uprising",
  air_bombardment: "Air bombardment",
  occupation: "Occupation",
  evacuation: "Evacuation",
  urban_battle: "Urban battle",
  other: "Other",
};

/**
 * Build the DR bar-chart using D3 inside `container`.
 * @param {string} mode - "episode" (default) or "conflict"
 */
export function initDRChart(container, bundles, { onBarClick, mode = "episode" } = {}) {
  if (!container || !bundles?.length) return;

  const items = mode === "episode" ? buildEpisodeData(bundles) : buildConflictData(bundles);
  if (!items.length) {
    container.innerHTML = `<p class="chart-empty">No ${mode === "episode" ? "episodes" : "conflicts"} with RR estimates yet.</p>`;
    return;
  }

  const sortMode = container.dataset.sort || "dr-asc";
  sortItems(items, sortMode);

  const d3 = window.d3;
  if (!d3) {
    container.innerHTML = `<p class="chart-empty">D3 not loaded.</p>`;
    return;
  }

  // ── Grouped sort modes ──
  const isGrouped = sortMode === "victim" || sortMode === "inflicting" || sortMode === "type";
  const groupKey = sortMode === "victim"
    ? (d) => d.victimSide || "Unknown"
    : sortMode === "inflicting"
      ? (d) => d.inflictingSide || "Unknown"
      : sortMode === "type"
        ? (d) => d.episodeType
        : () => null;
  const groupLabel = sortMode === "type"
    ? (key) => TYPE_LABELS[key] || key
    : (key) => key;

  // ── Dimensions ──
  const deathsAxisWidth = 120;
  const deathsLabelPad = 36;
  const margin = { top: 52, right: deathsAxisWidth + deathsLabelPad + 16, bottom: 48, left: 0 };
  const labelWidth = 300;
  const barHeight = mode === "episode" ? 36 : 28;
  const barGap = mode === "episode" ? 6 : 4;
  // Count group breaks for extra spacing
  let groupBreakCount = 0;
  if (isGrouped) {
    for (let i = 1; i < items.length; i++) {
      if (groupKey(items[i]) !== groupKey(items[i - 1])) groupBreakCount++;
    }
  }
  const countryGap = 28;
  const chartHeight = items.length * (barHeight + barGap) + groupBreakCount * countryGap + margin.top + margin.bottom;
  const containerWidth = container.clientWidth || 900;
  const width = Math.max(600, containerWidth);
  const innerWidth = width - margin.left - margin.right - labelWidth;
  const innerHeight = chartHeight - margin.top - margin.bottom;

  container.innerHTML = "";

  const svg = d3
    .select(container)
    .append("svg")
    .attr("class", "dr-chart-svg")
    .attr("width", width)
    .attr("height", chartHeight)
    .attr("viewBox", `0 0 ${width} ${chartHeight}`)
    .attr("preserveAspectRatio", "xMinYMin meet");

  // Clip path to prevent bars from bleeding into the label area
  const clipId = `chart-clip-${Date.now()}`;
  svg.append("defs").append("clipPath")
    .attr("id", clipId)
    .append("rect")
    .attr("x", -2)
    .attr("y", -margin.top)
    .attr("width", innerWidth + margin.right + 4)
    .attr("height", chartHeight + margin.top);

  const g = svg.append("g")
    .attr("transform", `translate(${margin.left + labelWidth},${margin.top})`)
    .attr("clip-path", `url(#${clipId})`);

  // ── Scales ──
  const allValues = items.flatMap((d) => [d.drLow, d.drHigh, d.drBest].filter((v) => v > 0));
  const domainMin = Math.max(0.005, d3.min(allValues) * 0.5);
  const domainMax = d3.max(allValues) * 2;

  const x = d3.scaleLog().domain([domainMin, domainMax]).range([0, innerWidth]).clamp(true);

  // Build y positions with extra gaps at group breaks
  const yPos = new Map();
  let cumY = 0;
  for (let i = 0; i < items.length; i++) {
    if (i > 0 && isGrouped && groupKey(items[i]) !== groupKey(items[i - 1])) {
      cumY += countryGap;
    }
    yPos.set(items[i].id, cumY);
    cumY += barHeight + barGap;
  }
  const yBandwidth = barHeight;
  // y() returns the top of the bar for a given item id
  const y = (id) => yPos.get(id) ?? 0;
  y.bandwidth = () => yBandwidth;

  // ── Grid lines ──
  const ticks = [0.01, 0.1, 1, 10, 100];
  g.append("g")
    .attr("class", "chart-grid")
    .selectAll("line")
    .data(ticks.filter((t) => t >= domainMin && t <= domainMax))
    .join("line")
    .attr("x1", (d) => x(d))
    .attr("x2", (d) => x(d))
    .attr("y1", 0)
    .attr("y2", innerHeight);

  // ── RR = 1 reference line ──
  const x1 = x(1);
  g.append("line")
    .attr("class", "chart-ref-line")
    .attr("x1", x1)
    .attr("x2", x1)
    .attr("y1", -36)
    .attr("y2", innerHeight + 8);

  g.append("text")
    .attr("class", "chart-ref-label")
    .attr("x", x1)
    .attr("y", -30)
    .attr("text-anchor", "middle")
    .text("RR = 1");

  g.append("text")
    .attr("class", "chart-zone-label")
    .attr("x", x1 - 12)
    .attr("y", -14)
    .attr("text-anchor", "end")
    .text("\u2190 Civilians at higher risk");

  g.append("text")
    .attr("class", "chart-zone-label")
    .attr("x", x1 + 12)
    .attr("y", -14)
    .attr("text-anchor", "start")
    .text("Military at higher risk \u2192");

  // ── Group separators (country or episode type) ──
  // Rendered outside the clipped `g` so labels in the label area are visible.
  if (isGrouped) {
    const breaks = [];
    for (let i = 1; i < items.length; i++) {
      if (groupKey(items[i]) !== groupKey(items[i - 1])) {
        const prevBottom = y(items[i - 1].id) + y.bandwidth();
        const nextTop = y(items[i].id);
        const midY = (prevBottom + nextTop) / 2;
        breaks.push({ yPos: midY, label: groupLabel(groupKey(items[i])) });
      }
    }

    const sepGroup = svg.append("g")
      .attr("class", "chart-country-seps")
      .attr("transform", `translate(${margin.left + labelWidth},${margin.top})`);

    // Divider line across full width
    sepGroup.selectAll(".chart-country-divider")
      .data(breaks)
      .join("line")
      .attr("class", "chart-country-divider")
      .attr("x1", -labelWidth)
      .attr("x2", innerWidth)
      .attr("y1", (d) => d.yPos)
      .attr("y2", (d) => d.yPos);

    // Group label: left-aligned, just below the divider line
    sepGroup.selectAll(".chart-country-label")
      .data(breaks)
      .join("text")
      .attr("class", "chart-country-label")
      .attr("x", -labelWidth + 4)
      .attr("y", (d) => d.yPos + 12)
      .attr("text-anchor", "start")
      .text((d) => d.label);

    // First group label (no divider, just the name above first item)
    if (items.length) {
      sepGroup.append("text")
        .attr("class", "chart-country-label")
        .attr("x", -labelWidth + 4)
        .attr("y", y(items[0].id) - 4)
        .attr("text-anchor", "start")
        .text(groupLabel(groupKey(items[0])));
    }
  }

  // ── Uncertainty range bars (low to high) ──
  g.selectAll(".chart-range-bar")
    .data(items.filter((d) => d.drLow !== d.drHigh))
    .join("rect")
    .attr("class", "chart-range-bar")
    .attr("x", (d) => x(d.drLow))
    .attr("y", (d) => y(d.id) + y.bandwidth() * 0.2)
    .attr("width", (d) => Math.max(1, x(d.drHigh) - x(d.drLow)))
    .attr("height", y.bandwidth() * 0.6)
    .attr("rx", 3);

  // ── Best-estimate bars ──
  const barGroup = g
    .selectAll(".chart-bar-g")
    .data(items)
    .join("g")
    .attr("class", "chart-bar-g")
    .style("cursor", "pointer");

  barGroup
    .append("rect")
    .attr("class", (d) => `chart-bar ${d.drBest < 1 ? "chart-bar--civ" : "chart-bar--mil"}`)
    .attr("x", (d) => x(Math.min(d.drBest, 1)))
    .attr("y", (d) => y(d.id) + y.bandwidth() * 0.1)
    .attr("width", (d) => Math.max(3, Math.abs(x(d.drBest) - x(1))))
    .attr("height", y.bandwidth() * 0.8)
    .attr("rx", 4);

  // ── Marker dot ──
  barGroup
    .append("circle")
    .attr("class", "chart-marker")
    .attr("cx", (d) => x(d.drBest))
    .attr("cy", (d) => y(d.id) + y.bandwidth() / 2)
    .attr("r", 4);

  // ── RR value label ──
  // For bars near the left edge, flip label to the right side so it doesn't overlap names
  const valueLabelFlip = (d) => {
    if (d.drBest >= 1) return { x: x(d.drBest) + 10, anchor: "start" };
    if (x(d.drBest) < 40) return { x: x(d.drBest) + 10, anchor: "start" };
    return { x: x(d.drBest) - 10, anchor: "end" };
  };
  barGroup
    .append("text")
    .attr("class", "chart-bar-value")
    .attr("x", (d) => valueLabelFlip(d).x)
    .attr("y", (d) => y(d.id) + y.bandwidth() / 2)
    .attr("text-anchor", (d) => valueLabelFlip(d).anchor)
    .attr("dy", "0.35em")
    .text((d) => formatMetricNumber(d.drBest, "dr_v1_direct"));

  // ── Tooltip (created early so labels can use it too) ──
  const tooltip = d3
    .select(container)
    .append("div")
    .attr("class", "chart-tooltip")
    .style("display", "none");

  const showTip = (event, html) => {
    tooltip.style("display", "block").html(html);
    moveTip(event);
  };
  const moveTip = (event) => {
    const rect = container.getBoundingClientRect();
    const tipNode = tooltip.node();
    let left = event.clientX - rect.left + 14;
    let top = event.clientY - rect.top - 10;
    // Clamp so tooltip doesn't overflow container right edge
    const tipW = tipNode.offsetWidth || 200;
    if (left + tipW > rect.width) {
      left = event.clientX - rect.left - tipW - 14;
    }
    tooltip
      .style("left", `${left}px`)
      .style("top", `${top}px`);
  };
  const hideTip = () => tooltip.style("display", "none");

  // ── Left-side labels ──
  const labelGroup = svg
    .append("g")
    .attr("transform", `translate(0,${margin.top})`);

  if (mode === "episode") {
    const labelG = labelGroup
      .selectAll(".chart-label-g")
      .data(items)
      .join("g")
      .attr("class", "chart-label-g")
      .style("cursor", "pointer")
      .on("click", (event, d) => onBarClick?.(d.bundleId, d.episodeId))
      .on("mouseenter", (event, d) => {
        if (d.name.length > 38 || d.conflictName.length > 38) {
          showTip(event, `<strong>${escapeHtml(d.name)}</strong><div class="chart-tooltip__conflict">${escapeHtml(d.conflictName)}</div>`);
        }
      })
      .on("mousemove", (event) => moveTip(event))
      .on("mouseleave", () => hideTip());

    labelG
      .append("text")
      .attr("class", "chart-label")
      .attr("x", labelWidth - 12)
      .attr("y", (d) => y(d.id) + y.bandwidth() / 2 - 6)
      .attr("text-anchor", "end")
      .attr("dy", "0.35em")
      .text((d) => truncate(d.name, 38));

    labelG
      .append("text")
      .attr("class", "chart-label-sub")
      .attr("x", labelWidth - 12)
      .attr("y", (d) => y(d.id) + y.bandwidth() / 2 + 7)
      .attr("text-anchor", "end")
      .attr("dy", "0.35em")
      .text((d) => truncate(d.conflictName, 38));
  } else {
    const conflictLabelG = labelGroup
      .selectAll(".chart-label-g")
      .data(items)
      .join("g")
      .attr("class", "chart-label-g")
      .style("cursor", "pointer")
      .on("click", (event, d) => onBarClick?.(d.bundleId))
      .on("mouseenter", (event, d) => {
        if (d.name.length > 38) {
          showTip(event, `<strong>${escapeHtml(d.name)}</strong>`);
        }
      })
      .on("mousemove", (event) => moveTip(event))
      .on("mouseleave", () => hideTip());

    conflictLabelG
      .append("text")
      .attr("class", "chart-label")
      .attr("x", labelWidth - 12)
      .attr("y", (d) => y(d.id) + y.bandwidth() / 2)
      .attr("text-anchor", "end")
      .attr("dy", "0.35em")
      .text((d) => truncate(d.name, 38));
  }

  // ── X axis ──
  const xAxis = d3
    .axisBottom(x)
    .tickValues(ticks.filter((t) => t >= domainMin && t <= domainMax))
    .tickFormat((d) => (d >= 1 ? d3.format(",.0f")(d) : d3.format(".2f")(d)));

  g.append("g")
    .attr("class", "chart-x-axis")
    .attr("transform", `translate(0,${innerHeight})`)
    .call(xAxis);

  g.append("text")
    .attr("class", "chart-axis-label")
    .attr("x", innerWidth / 2)
    .attr("y", innerHeight + 40)
    .attr("text-anchor", "middle")
    .text("Relative Risk (log scale)");

  // ── Secondary axis: stacked deaths mini-bars (right side) ──
  const deathValues = items.map((d) => d.totalDeaths).filter((v) => v > 0);
  if (deathValues.length) {
    const dMax = d3.max(deathValues);
    const xDeaths = d3.scaleLog()
      .domain([1, dMax])
      .range([0, deathsAxisWidth])
      .clamp(true);

    const dg = svg.append("g")
      .attr("transform", `translate(${margin.left + labelWidth + innerWidth + 16},${margin.top})`);

    // Axis at bottom
    const deathTicks = [10, 100, 1000, 10000, 100000, 1000000].filter((t) => t <= dMax * 2);
    const deathAxis = d3.axisBottom(xDeaths)
      .tickValues(deathTicks)
      .tickFormat((d) => d >= 1000000 ? `${d / 1000000}M` : d >= 1000 ? `${d / 1000}k` : d);

    dg.append("g")
      .attr("class", "chart-x-axis chart-deaths-axis")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(deathAxis);

    dg.append("text")
      .attr("class", "chart-axis-label")
      .attr("x", deathsAxisWidth / 2)
      .attr("y", innerHeight + 40)
      .attr("text-anchor", "middle")
      .text("Deaths (log scale)");

    // Grid lines
    dg.append("g")
      .attr("class", "chart-grid")
      .selectAll("line")
      .data(deathTicks)
      .join("line")
      .attr("x1", (d) => xDeaths(d))
      .attr("x2", (d) => xDeaths(d))
      .attr("y1", 0)
      .attr("y2", innerHeight);

    const miniBarH = Math.min(y.bandwidth() * 0.5, 12);
    const miniBarY = (d) => y(d.id) + (y.bandwidth() - miniBarH) / 2;

    // Stacked mini-bar per row: military (teal) then civilian (red)
    const rowG = dg.selectAll(".chart-deaths-row")
      .data(items.filter((d) => d.totalDeaths > 0))
      .join("g")
      .attr("class", "chart-deaths-row");

    // Proportional split within log-scaled total width
    const milFrac = (d) => d.totalDeaths > 0 ? d.milDeaths / d.totalDeaths : 0;
    const totalW = (d) => Math.max(2, xDeaths(d.totalDeaths));

    // Military segment (starts at 0, proportional width)
    rowG.append("rect")
      .attr("class", "chart-deaths-mil")
      .attr("x", 0)
      .attr("y", (d) => miniBarY(d))
      .attr("width", (d) => d.milDeaths > 0 ? Math.max(1, totalW(d) * milFrac(d)) : 0)
      .attr("height", miniBarH)
      .attr("rx", 2);

    // Civilian segment (proportional width, starts after military)
    rowG.append("rect")
      .attr("class", "chart-deaths-civ")
      .attr("x", (d) => totalW(d) * milFrac(d))
      .attr("y", (d) => miniBarY(d))
      .attr("width", (d) => d.civDeaths > 0 ? Math.max(1, totalW(d) * (1 - milFrac(d))) : 0)
      .attr("height", miniBarH)
      .attr("rx", 2);

    // Total deaths label above the bar
    rowG.append("text")
      .attr("class", "chart-deaths-label")
      .attr("x", (d) => xDeaths(d.totalDeaths) + 4)
      .attr("y", (d) => miniBarY(d) + miniBarH / 2)
      .attr("dy", "0.35em")
      .text((d) => formatDeathCount(d.totalDeaths));

    // Tooltip on mini-bars
    rowG
      .on("mouseenter", (event, d) => {
        const lines = [`<strong>${formatDeathCount(d.totalDeaths)} total deaths</strong>`];
        lines.push(`Civilian: ${formatDeathCount(d.civDeaths)}`);
        const milLabel = d.milLowFlag
          ? `${formatDeathCount(d.milDeaths)}* <span style="color:var(--muted)">(very low / sources may confirm zero)</span>`
          : formatDeathCount(d.milDeaths);
        lines.push(`Military: ${milLabel}`);
        if (d.childDeaths > 0) lines.push(`Children: ${formatDeathCount(d.childDeaths)}`);
        if (d.womenDeaths > 0) lines.push(`Women: ${formatDeathCount(d.womenDeaths)}`);
        if (d.unknownDeaths > 0) lines.push(`Unknown status: ${formatDeathCount(d.unknownDeaths)}`);
        showTip(event, lines.join("<br>"));
      })
      .on("mousemove", (event) => moveTip(event))
      .on("mouseleave", () => hideTip());
  }

  barGroup
    .on("mouseenter", (event, d) => {
      const rangeText =
        d.drLow !== d.drHigh
          ? `Range: ${formatMetricNumber(d.drLow, "dr_v1_direct")} \u2013 ${formatMetricNumber(d.drHigh, "dr_v1_direct")}`
          : "";
      const subLabel = mode === "episode"
        ? `<div class="chart-tooltip__conflict">${escapeHtml(d.conflictName)}</div>`
        : d.episodeCount ? `<div class="chart-tooltip__conflict">Avg of ${d.episodeCount} episode${d.episodeCount > 1 ? "s" : ""}</div>` : "";
      const drLabel = mode === "conflict" ? "Avg RR" : "Best RR";
      const typeLabel = TYPE_LABELS[d.episodeType] || d.episodeType;
      const excessText = d.excessCiv != null
        ? `<div class="chart-tooltip__excess">${d.excessCiv > 0 ? "+" : ""}${d.excessCiv.toLocaleString()} excess civ. deaths vs parity</div>`
        : "";
      const milNote = d.milLowFlag ? ` <span style="color:var(--warning)">mil\u2009=\u2009${d.milDeaths}*</span>` : "";
      const deathsText = d.totalDeaths
        ? `<div>${d.totalDeaths.toLocaleString()} total deaths${milNote}</div>`
        : "";
      showTip(event, `
        <strong>${escapeHtml(d.name)}</strong>
        ${subLabel}
        <div>${drLabel}: ${formatMetricNumber(d.drBest, "dr_v1_direct")}</div>
        ${rangeText ? `<div>${rangeText}</div>` : ""}
        ${deathsText}
        ${excessText}
        <div class="chart-tooltip__tier">${escapeHtml(typeLabel)} · ${escapeHtml(d.tier || "No tier")}</div>
        <div class="chart-tooltip__dates">${escapeHtml(d.dates)}</div>
      `);
    })
    .on("mousemove", (event) => moveTip(event))
    .on("mouseleave", () => hideTip())
    .on("click", (event, d) => onBarClick?.(d.bundleId, d.episodeId));
}

// ── Data builders ──

function buildEpisodeData(bundles) {
  const items = [];
  for (const b of bundles) {
    for (const ep of b.episodes || []) {
      const drRow = (ep.metric_rows || []).find(
        (m) => m.metric_name === "dr_v1_direct" && m.value_best != null,
      );
      if (!drRow) continue;

      const best = Number(drRow.value_best);
      const low = drRow.value_low != null ? Number(drRow.value_low) : best;
      const high = drRow.value_high != null ? Number(drRow.value_high) : best;
      if (best <= 0) continue;

      // Extract component metrics for excess-deaths calculation
      const metrics = extractComponentMetrics(ep.metric_rows);
      const totalDeaths = metrics.civDeaths + metrics.milDeaths;
      const excessCiv = computeExcessCivDeaths(metrics);

      items.push({
        id: `${b.bundle_id}::${ep.episode_id}`,
        bundleId: b.bundle_id,
        episodeId: ep.episode_id,
        name: ep.episode_name || ep.episode_id,
        conflictName: b.conflict_name || b.bundle_id,
        victimSide: ep.victim_country || (ep.countries || b.countries || [])[0] || "Unknown",
        inflictingSide: ep.inflicting_country || null,
        episodeType: ep.primary_episode_type || "other",
        drBest: Math.max(0.001, best),
        drLow: Math.max(0.001, low),
        drHigh: Math.max(0.001, high),
        tier: drRow.quality_tier || ep.quality_tier || null,
        dates: formatDateRangeSimple(ep.start_date, ep.end_date),
        civDeaths: metrics.civDeaths,
        milDeaths: metrics.milDeaths,
        milLowFlag: metrics.milDeaths <= 5 && metrics.civDeaths >= 50,
        milZeroConfirmed: metrics.milZeroConfirmed,
        womenDeaths: metrics.womenDeaths,
        childDeaths: metrics.childDeaths,
        unknownDeaths: metrics.unknownDeaths,
        totalDeaths,
        excessCiv,
      });
    }
  }
  return items;
}

function buildConflictData(bundles) {
  const items = [];
  for (const b of bundles) {
    // Collect all episode-level DR best values, types, and deaths for this conflict
    const epDRs = [];
    const typeCounts = {};
    let conflictCivDeaths = 0, conflictMilDeaths = 0, conflictWomen = 0, conflictChildren = 0, conflictUnknown = 0;
    let conflictExcessCiv = 0;
    for (const ep of b.episodes || []) {
      const drRow = (ep.metric_rows || []).find(
        (m) => m.metric_name === "dr_v1_direct" && m.value_best != null,
      );
      if (drRow) {
        epDRs.push(Number(drRow.value_best));
        const t = ep.primary_episode_type || "other";
        typeCounts[t] = (typeCounts[t] || 0) + 1;
        const metrics = extractComponentMetrics(ep.metric_rows);
        conflictCivDeaths += metrics.civDeaths;
        conflictMilDeaths += metrics.milDeaths;
        conflictWomen += metrics.womenDeaths;
        conflictChildren += metrics.childDeaths;
        conflictUnknown += metrics.unknownDeaths;
        conflictExcessCiv += computeExcessCivDeaths(metrics);
      }
    }
    if (!epDRs.length) continue;

    // Average of episode DRs as the representative value
    const drBest = epDRs.reduce((s, v) => s + v, 0) / epDRs.length;
    const drLow = Math.min(...epDRs);
    const drHigh = Math.max(...epDRs);

    // Most common episode type for this conflict
    const primaryType = Object.entries(typeCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || "other";

    // Use the most common victim/inflicting side from episodes
    const victimCounts = {};
    const inflictingCounts = {};
    for (const ep of b.episodes || []) {
      if (ep.victim_country) victimCounts[ep.victim_country] = (victimCounts[ep.victim_country] || 0) + 1;
      if (ep.inflicting_country) inflictingCounts[ep.inflicting_country] = (inflictingCounts[ep.inflicting_country] || 0) + 1;
    }
    const topVictim = Object.entries(victimCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || (b.countries || [])[0] || "Unknown";
    const topInflicting = Object.entries(inflictingCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || null;

    items.push({
      id: b.bundle_id,
      bundleId: b.bundle_id,
      episodeId: null,
      name: b.conflict_name || b.bundle_id,
      conflictName: b.conflict_name || b.bundle_id,
      victimSide: topVictim,
      inflictingSide: topInflicting,
      episodeType: primaryType,
      drBest: Math.max(0.001, drBest),
      drLow: Math.max(0.001, drLow),
      drHigh: Math.max(0.001, drHigh),
      tier: b.quality_band || null,
      dates: formatDateRangeSimple(b.start_date, b.end_date),
      episodeCount: epDRs.length,
      civDeaths: conflictCivDeaths,
      milDeaths: conflictMilDeaths,
      milLowFlag: conflictMilDeaths <= 5 && conflictCivDeaths >= 50,
      milZeroConfirmed: false,
      womenDeaths: conflictWomen,
      childDeaths: conflictChildren,
      unknownDeaths: conflictUnknown,
      totalDeaths: conflictCivDeaths + conflictMilDeaths,
      excessCiv: conflictExcessCiv,
    });
  }
  return items;
}

function sortItems(items, mode) {
  switch (mode) {
    case "dr-asc":
      items.sort((a, b) => a.drBest - b.drBest);
      break;
    case "dr-desc":
      items.sort((a, b) => b.drBest - a.drBest);
      break;
    case "name":
      items.sort((a, b) => a.name.localeCompare(b.name));
      break;
    case "victim": {
      const sideDRs = {};
      for (const item of items) {
        const s = item.victimSide || "Unknown";
        if (!sideDRs[s]) sideDRs[s] = [];
        sideDRs[s].push(item.drBest);
      }
      const sideAvg = {};
      for (const [s, drs] of Object.entries(sideDRs)) {
        sideAvg[s] = drs.reduce((sum, v) => sum + v, 0) / drs.length;
      }
      items.sort((a, b) => {
        const cmp = (sideAvg[a.victimSide || "Unknown"] || 0) - (sideAvg[b.victimSide || "Unknown"] || 0);
        if (cmp !== 0) return cmp;
        return a.drBest - b.drBest;
      });
      break;
    }
    case "inflicting": {
      const sideDRs = {};
      for (const item of items) {
        const s = item.inflictingSide || "Unknown";
        if (!sideDRs[s]) sideDRs[s] = [];
        sideDRs[s].push(item.drBest);
      }
      const sideAvg = {};
      for (const [s, drs] of Object.entries(sideDRs)) {
        sideAvg[s] = drs.reduce((sum, v) => sum + v, 0) / drs.length;
      }
      items.sort((a, b) => {
        const cmp = (sideAvg[a.inflictingSide || "Unknown"] || 0) - (sideAvg[b.inflictingSide || "Unknown"] || 0);
        if (cmp !== 0) return cmp;
        return a.drBest - b.drBest;
      });
      break;
    }
    case "type": {
      // Compute average DR per episode type
      const typeDRs = {};
      for (const item of items) {
        const t = item.episodeType || "other";
        if (!typeDRs[t]) typeDRs[t] = [];
        typeDRs[t].push(item.drBest);
      }
      const typeAvg = {};
      for (const [t, drs] of Object.entries(typeDRs)) {
        typeAvg[t] = drs.reduce((s, v) => s + v, 0) / drs.length;
      }
      // Sort by type avg DR ascending, then by individual DR within type
      items.sort((a, b) => {
        const cmp = (typeAvg[a.episodeType] || 0) - (typeAvg[b.episodeType] || 0);
        if (cmp !== 0) return cmp;
        return a.drBest - b.drBest;
      });
      break;
    }
    case "excess":
      items.sort((a, b) => b.excessCiv - a.excessCiv);
      break;
    default:
      items.sort((a, b) => a.drBest - b.drBest);
  }
}

// ── Metric extraction helpers ──

/** Sum the best values for a given metric_name across all sides. */
function sumMetric(rows, name) {
  let total = 0;
  for (const r of rows) {
    if (r.metric_name === name && r.value_best != null) total += Number(r.value_best);
  }
  return total;
}

function extractComponentMetrics(metricRows) {
  const rows = metricRows || [];
  // Check if any mil_deaths_direct row has zero_confirmed flag
  const milRow = rows.find(r => r.metric_name === "mil_deaths_direct");
  const milZeroConfirmed = milRow?.zero_confirmed === true;
  return {
    civDeaths: sumMetric(rows, "civ_deaths_direct"),
    milDeaths: sumMetric(rows, "mil_deaths_direct"),
    milZeroConfirmed,
    civPM: sumMetric(rows, "civ_person_months"),
    milPM: sumMetric(rows, "mil_person_months"),
    womenDeaths: sumMetric(rows, "civ_deaths_women_direct"),
    childDeaths: sumMetric(rows, "civ_deaths_children_u18_direct")
      + sumMetric(rows, "civ_deaths_children_u15_direct")
      + sumMetric(rows, "civ_deaths_children_direct_unspecified_age_cutoff"),
    unknownDeaths: sumMetric(rows, "unknown_deaths_direct"),
  };
}

/**
 * Excess civilian deaths above what RR = 1 (parity) would predict.
 * At parity: expected_civ = mil_deaths × (civ_person_months / mil_person_months)
 * Positive = more civilians died than parity predicts.
 */
function computeExcessCivDeaths({ civDeaths, milDeaths, civPM, milPM }) {
  if (!milPM || !milDeaths) return 0;
  const expectedCiv = milDeaths * (civPM / milPM);
  return Math.round(civDeaths - expectedCiv);
}

function formatDeathCount(n) {
  if (n == null || n === 0) return "0";
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 10000) return `${Math.round(n / 1000)}k`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return n.toLocaleString();
}

function truncate(str, max) {
  if (!str) return "";
  return str.length > max ? str.slice(0, max - 1) + "\u2026" : str;
}

function formatDateRangeSimple(start, end) {
  const s = start ? new Date(start).getFullYear() : null;
  const e = end ? new Date(end).getFullYear() : null;
  if (s && e) return `${s}\u2013${e}`;
  if (s) return `${s}\u2013present`;
  if (e) return `\u2013${e}`;
  return "";
}

function measureLabel(text) {
  // Rough estimate: ~6.5px per character at 10px font
  return (text || "").length * 6.5;
}
