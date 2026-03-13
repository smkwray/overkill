/* ── World Map Module — Episode Hotspot View (D3 + TopoJSON) ── */

let cachedTopoData = null;
let cachedGeoLookup = null;
let currentSvg = null;
let currentProjection = null;
let currentMapData = null;
let currentTooltip = null;
let currentDecade = null;
let currentContainer = null;
let currentWorldGroup = null;
let currentHotspotGroup = null;
let currentZoom = null;

// ── Country ISO mapping (kept for country centroids fallback) ──
const COUNTRY_ISO = {
  "Afghanistan": 4, "Albania": 8, "Algeria": 12, "Angola": 24,
  "Argentina": 32, "Armenia": 51, "Azerbaijan": 31, "Bangladesh": 50,
  "Belarus": 112, "Bolivia": 68, "Bosnia and Herzegovina": 70,
  "Brazil": 76, "Burkina Faso": 854, "Burundi": 108, "Cambodia": 116,
  "Cameroon": 120, "Central African Republic": 140, "Chad": 148,
  "Chile": 152, "China": 156, "Colombia": 170, "Congo": 178,
  "Democratic Republic of the Congo": 180, "Croatia": 191,
  "Cuba": 192, "Cyprus": 196, "Djibouti": 262, "East Timor": 626,
  "Ecuador": 218, "Egypt": 818, "El Salvador": 222, "Eritrea": 232,
  "Ethiopia": 231, "France": 250, "Georgia": 268, "Germany": 276,
  "Greece": 300, "Guatemala": 320, "Guinea": 324, "Haiti": 332,
  "Honduras": 340, "India": 356, "Indonesia": 360, "Iran": 364,
  "Iraq": 368, "Israel": 376, "Ivory Coast": 384, "Japan": 392,
  "Jordan": 400, "Kenya": 404, "Korea": 410, "Kosovo": 383,
  "Kuwait": 414, "Laos": 418, "Lebanon": 422, "Liberia": 430,
  "Libya": 434, "Mali": 466, "Mexico": 484, "Moldova": 498,
  "Morocco": 504, "Mozambique": 508, "Myanmar": 104, "Namibia": 516,
  "Nepal": 524, "Nicaragua": 558, "Niger": 562, "Nigeria": 566,
  "North Korea": 408, "Pakistan": 586, "Palestine": 275,
  "Panama": 591, "Paraguay": 600, "Peru": 604, "Philippines": 608,
  "Poland": 616, "Russia": 643, "Rwanda": 646, "Saudi Arabia": 682,
  "Senegal": 686, "Serbia": 688, "Sierra Leone": 694,
  "Somalia": 706, "South Africa": 710, "South Korea": 410,
  "South Sudan": 728, "Spain": 724, "Sri Lanka": 144, "Sudan": 736,
  "Syria": 760, "Tajikistan": 762, "Tanzania": 834, "Thailand": 764,
  "Togo": 768, "Tunisia": 788, "Turkey": 792, "Turkmenistan": 795,
  "Uganda": 800, "Ukraine": 804, "United Kingdom": 826,
  "United States": 840, "Uruguay": 858, "Uzbekistan": 860,
  "Venezuela": 862, "Vietnam": 704, "Yemen": 887, "Zimbabwe": 716,
  "Russian Federation": 643,
  "North Vietnam": 704, "North Vietnam (Democratic Republic of Vietnam)": 704,
  "South Vietnam": 704, "South Vietnam (Republic of Vietnam)": 704,
  "Occupied Palestinian Territory": 275, "Palestinian territories": 275,
  "Israel / former Mandatory Palestine": 376,
  "Mandatory Palestine / Israel": 376,
  "North Macedonia": 807,
  "British Hong Kong": 156,
  "Ottoman Mesopotamia (present-day Iraq, partly)": 368,
  "Ottoman Syria (present-day Syria)": 760,
  "Ottoman Empire (present-day Turkey)": 792,
  "Transjordan / Jordan": 400,
  "Chechen Republic of Ichkeria (de facto)": 643,
  "United Arab Emirates": 784,
  "Australia": 36, "Canada": 124, "Finland": 246,
  "Hungary": 348, "Romania": 642, "Bulgaria": 100,
  "Singapore": 702, "Malaysia": 458,
  "Nazi Germany": 276, "West Germany": 276, "East Germany": 276,
  "Soviet Union": 643, "USSR": 643,
  "Ottoman Empire": 792,
  "Yugoslavia": 688, "Federal Republic of Yugoslavia": 688,
  "Czechoslovakia": 203, "Czech Republic": 203,
  "Zaire": 180, "Rhodesia": 716, "Burma": 104, "Persia": 364,
  "Siam": 764, "Abyssinia": 231, "Belgian Congo": 180,
  "French Indochina": 704,
  "Kingdom of Italy": 380, "Italy": 380,
  "Austria-Hungary": 40, "Austria": 40,
  "Republic of China": 156, "Taiwan": 158,
  "Mandatory Palestine": 275,
  "East Pakistan (present-day Bangladesh)": 50,
  "West Pakistan": 586,
  "French Algeria": 12,
  "Republic of Serbian Krajina": 191,
  "Republika Srpska": 70,
  "Democratic Kampuchea": 116,
};

const GEO_LOOKUP_PATHS = [
  "../data/index/geo_lookup.json",
  "./data/geo_lookup.json",
];

// ── Public API ──

export function getAvailableDecades(bundles) {
  const decades = new Set();
  for (const bundle of bundles || []) {
    for (const episode of bundle.episodes || []) {
      const date = episode.start_date || bundle.start_date;
      const year = date ? new Date(date).getFullYear() : null;
      if (year) decades.add(Math.floor(year / 10) * 10);
    }
    const startYear = bundle.start_date ? new Date(bundle.start_date).getFullYear() : null;
    if (startYear) decades.add(Math.floor(startYear / 10) * 10);
  }
  return [...decades].sort((a, b) => a - b);
}

export async function initMap(container, overview, decade) {
  const d3 = window.d3;
  const topojson = window.topojson;

  if (!d3 || !topojson) {
    container.innerHTML = `
      <div class="map-fallback">
        <p>Map visualization requires D3.js which failed to load from CDN.</p>
      </div>
    `;
    return;
  }

  currentDecade = decade;
  currentContainer = container;

  // Load TopoJSON world data
  if (!cachedTopoData) {
    try {
      cachedTopoData = await d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json");
    } catch {
      container.innerHTML = `<div class="map-fallback"><p>Could not load world map data.</p></div>`;
      return;
    }
  }

  // Load geo lookup
  if (!cachedGeoLookup) {
    cachedGeoLookup = await loadGeoLookup();
  }

  // Prepare episode hotspot data
  currentMapData = prepareHotspotData(overview?.bundles, cachedGeoLookup, cachedTopoData);

  const width = container.clientWidth || 960;
  const height = container.clientHeight || 500;

  // Clear previous
  container.querySelectorAll("svg.map-svg").forEach((el) => el.remove());
  if (currentTooltip) { currentTooltip.remove(); currentTooltip = null; }

  const svg = d3.select(container)
    .append("svg")
    .attr("class", "map-svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid slice");

  currentSvg = svg;

  const projection = d3.geoNaturalEarth1()
    .fitSize([width - 8, height - 8], { type: "Sphere" })
    .translate([width / 2, height / 2]);

  currentProjection = projection;
  const path = d3.geoPath(projection);

  const countries = topojson.feature(cachedTopoData, cachedTopoData.objects.countries);
  const borders = topojson.mesh(cachedTopoData, cachedTopoData.objects.countries, (a, b) => a !== b);

  // World group — zoom transforms this
  const worldGroup = svg.append("g").attr("class", "map-world");
  currentWorldGroup = worldGroup;

  // Ocean
  worldGroup.append("path")
    .datum({ type: "Sphere" })
    .attr("class", "map-sphere")
    .attr("d", path)
    .attr("fill", getOceanColor())
    .attr("stroke", getBorderColor());

  // Neutral country fills
  worldGroup.selectAll(".map-country")
    .data(countries.features)
    .enter()
    .append("path")
    .attr("class", "map-country")
    .attr("d", path)
    .attr("fill", getNeutralColor())
    .attr("stroke", getBorderColor())
    .attr("stroke-width", 0.5);

  // Borders
  worldGroup.append("path")
    .datum(borders)
    .attr("class", "map-borders")
    .attr("d", path)
    .attr("fill", "none")
    .attr("stroke", getBorderColor())
    .attr("stroke-width", 0.3);

  // Hotspot layer (on top of countries)
  const hotspotGroup = worldGroup.append("g").attr("class", "map-hotspots");
  currentHotspotGroup = hotspotGroup;

  // Render hotspots for current decade
  renderHotspots(decade);

  // Zoom behavior
  const zoom = d3.zoom()
    .scaleExtent([1, 12])
    .on("zoom", (event) => {
      worldGroup.attr("transform", event.transform);
    });

  currentZoom = zoom;
  svg.call(zoom);

  svg.on("dblclick.zoom", () => {
    svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
  });
}

export function updateMapDecade(decade) {
  if (!currentSvg || !currentMapData) return;
  currentDecade = decade;
  renderHotspots(decade);
}

export function refreshMapTheme() {
  if (!currentSvg) return;
  currentSvg.select(".map-sphere")
    .attr("fill", getOceanColor())
    .attr("stroke", getBorderColor());
  currentSvg.selectAll(".map-country")
    .attr("fill", getNeutralColor())
    .attr("stroke", getBorderColor());
  currentSvg.select(".map-borders")
    .attr("stroke", getBorderColor());
}

export function destroyMap() {
  if (currentSvg) { currentSvg.remove(); currentSvg = null; }
  if (currentTooltip) { currentTooltip.remove(); currentTooltip = null; }
  currentProjection = null;
  currentMapData = null;
  currentDecade = null;
  currentContainer = null;
  currentWorldGroup = null;
  currentHotspotGroup = null;
  currentZoom = null;
}

// ── Hotspot rendering ──

function renderHotspots(decade) {
  const d3 = window.d3;
  if (!d3 || !currentHotspotGroup || !currentMapData || !currentProjection) return;

  // Only show hotspots for episodes that have an RR estimate
  const episodes = currentMapData.episodes.filter((ep) => ep.decade === decade && ep.hasDR);

  // Size scale: circle radius by DR magnitude (log distance from 1)
  // DR=1 is neutral, farther from 1 in either direction → larger circle
  const drMagnitude = (d) => Math.abs(Math.log10(Math.max(0.001, d.drBest)));
  const maxMag = Math.max(0.5, ...episodes.map(drMagnitude));
  const rScale = d3.scaleLinear().domain([0, maxMag]).range([6, 26]).clamp(true);

  // Clear previous hotspots
  currentHotspotGroup.selectAll("*").remove();

  // Sort so smaller circles render on top (larger DR magnitude → draw first)
  const sorted = [...episodes].sort((a, b) => drMagnitude(b) - drMagnitude(a));

  const groups = currentHotspotGroup
    .selectAll(".hotspot")
    .data(sorted, (d) => d.key)
    .join("g")
    .attr("class", "hotspot")
    .attr("transform", (d) => {
      const [px, py] = currentProjection([d.lon, d.lat]);
      return `translate(${px},${py})`;
    })
    .style("cursor", "pointer");

  // Outer glow
  groups.append("circle")
    .attr("class", "hotspot-glow")
    .attr("r", (d) => rScale(drMagnitude(d)) + 4)
    .attr("fill", (d) => d.drBest < 1 ? "var(--danger)" : "var(--accent)")
    .attr("opacity", 0.15);

  // Main circle
  groups.append("circle")
    .attr("class", "hotspot-circle")
    .attr("r", (d) => rScale(drMagnitude(d)))
    .attr("fill", (d) => d.drBest < 1 ? "var(--danger)" : "var(--accent)")
    .attr("opacity", 0.55)
    .attr("stroke", (d) => d.drBest < 1 ? "var(--danger)" : "var(--accent)")
    .attr("stroke-width", 1.5)
    .attr("stroke-opacity", 0.8);

  // Center dot
  groups.append("circle")
    .attr("class", "hotspot-center")
    .attr("r", 2.5)
    .attr("fill", "var(--text)")
    .attr("opacity", 0.9);

  // Interactions
  groups
    .on("mouseenter", (event, d) => showHotspotTooltip(event, d))
    .on("mousemove", (event) => moveTooltip(event))
    .on("mouseleave", () => hideTooltip())
    .on("click", (event, d) => {
      currentContainer.dispatchEvent(new CustomEvent("map-country-click", {
        detail: { bundleId: d.bundleId },
        bubbles: true,
      }));
    });

  // Fade in
  groups.attr("opacity", 0)
    .transition()
    .duration(400)
    .attr("opacity", 1);
}

// ── Data preparation ──

function prepareHotspotData(bundles, geoLookup, topoData) {
  const episodes = [];
  const countryCentroids = computeCountryCentroids(topoData);

  for (const bundle of bundles || []) {
    for (const episode of bundle.episodes || []) {
      const startDate = episode.start_date || bundle.start_date;
      const startYear = startDate ? new Date(startDate).getFullYear() : null;
      const decade = startYear ? Math.floor(startYear / 10) * 10 : null;
      if (!decade) continue;

      // Find coordinates: try admin_units first, then country centroid
      const coords = resolveCoords(
        episode.admin_units || [],
        episode.countries || bundle.countries || [],
        geoLookup,
        countryCentroids,
      );
      if (!coords) continue;

      // Extract metrics
      let civDeaths = 0;
      let drBest = null;
      for (const m of episode.metric_rows || []) {
        if (m.metric_name === "civ_deaths_direct" && m.value_best != null) {
          civDeaths += Number(m.value_best) || 0;
        }
        if (m.metric_name === "dr_v1_direct" && m.value_best != null) {
          drBest = Number(m.value_best);
        }
      }

      episodes.push({
        key: `${bundle.bundle_id}::${episode.episode_id}`,
        bundleId: bundle.bundle_id,
        episodeId: episode.episode_id,
        episodeName: episode.episode_name || episode.episode_id,
        conflictName: bundle.conflict_name || bundle.bundle_id,
        lat: coords.lat,
        lon: coords.lon,
        decade,
        civDeaths,
        hasDR: drBest !== null,
        drBest: drBest ?? 0,
        qualityTier: episode.quality_tier || null,
        geoScope: episode.geographic_scope || "",
        dates: formatDateRange(episode.start_date, episode.end_date),
      });
    }
  }

  return { episodes };
}

function resolveCoords(adminUnits, countries, geoLookup, countryCentroids) {
  // Try each admin_unit in the geo lookup
  for (const unit of adminUnits) {
    const entry = geoLookup[unit];
    if (entry) return { lat: entry.lat, lon: entry.lon };
  }

  // Fallback: country centroid
  for (const country of countries) {
    const iso = COUNTRY_ISO[country];
    if (iso && countryCentroids[iso]) {
      return countryCentroids[iso];
    }
  }

  return null;
}

function computeCountryCentroids(topoData) {
  const d3 = window.d3;
  const topojson = window.topojson;
  const centroids = {};

  if (!d3 || !topojson || !topoData) return centroids;

  const countries = topojson.feature(topoData, topoData.objects.countries);
  for (const feature of countries.features) {
    const [lon, lat] = d3.geoCentroid(feature);
    centroids[Number(feature.id)] = { lat, lon };
  }

  return centroids;
}

async function loadGeoLookup() {
  for (const path of GEO_LOOKUP_PATHS) {
    try {
      const resp = await fetch(path, { credentials: "same-origin" });
      if (resp.ok) return await resp.json();
    } catch { /* try next */ }
  }
  console.warn("Could not load geo_lookup.json — falling back to country centroids only");
  return {};
}

// ── Theme helpers ──

function getNeutralColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--surface-tint-strong").trim() || "rgba(255,255,255,0.06)";
}

function getBorderColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--border").trim() || "rgba(255,255,255,0.08)";
}

function getOceanColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--panel-strong").trim() || "#1f2731";
}

// ── Tooltip ──

function computePercentileLabel(drBest, allEpisodes) {
  if (!allEpisodes || !allEpisodes.length) return "";
  const sorted = allEpisodes.filter((e) => e.hasDR).map((e) => e.drBest).sort((a, b) => a - b);
  if (!sorted.length) return "";
  const rank = sorted.filter((v) => v <= drBest).length;
  const pct = Math.round((rank / sorted.length) * 100);
  if (pct <= 10) return `Bottom 10% of RR (most civilian-skewed)`;
  if (pct >= 90) return `Top 10% of RR (most military-skewed)`;
  return `${ordinal(pct)} percentile of RR`;
}

function ordinal(n) {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function showHotspotTooltip(event, d) {
  if (!currentTooltip) {
    currentTooltip = document.createElement("div");
    currentTooltip.className = "map-tooltip";
    currentContainer.appendChild(currentTooltip);
  }

  let html = `<strong>${esc(d.episodeName)}</strong>`;
  html += `<div class="map-tooltip__conflict-name">${esc(d.conflictName)}</div>`;

  if (d.hasDR) {
    const drFormatted = d.drBest >= 10 ? d.drBest.toFixed(1) : d.drBest >= 1 ? d.drBest.toFixed(2) : d.drBest.toFixed(3);
    const pctLabel = computePercentileLabel(d.drBest, currentMapData?.episodes);
    html += `<div class="map-tooltip__dr">RR: ${drFormatted}</div>`;
    if (pctLabel) html += `<div class="map-tooltip__pct">${pctLabel}</div>`;
  }

  if (d.civDeaths > 0) {
    html += `<div class="map-tooltip__deaths">${new Intl.NumberFormat().format(d.civDeaths)} est. civilian deaths</div>`;
  }

  if (d.geoScope) {
    html += `<div class="map-tooltip__scope">${esc(d.geoScope)}</div>`;
  }

  html += `<div class="map-tooltip__dates">${esc(d.dates)}</div>`;
  html += `<div class="map-tooltip__hint">Click to explore</div>`;

  currentTooltip.innerHTML = html;
  currentTooltip.style.display = "block";
  moveTooltip(event);
}

function moveTooltip(event) {
  if (!currentTooltip || !currentContainer) return;
  const rect = currentContainer.getBoundingClientRect();
  const tooltipWidth = currentTooltip.offsetWidth || 200;
  let x = event.clientX - rect.left + 14;
  let y = event.clientY - rect.top - 14;
  if (x + tooltipWidth + 10 > rect.width) x = event.clientX - rect.left - tooltipWidth - 10;
  if (y < 0) y = event.clientY - rect.top + 20;
  currentTooltip.style.left = `${x}px`;
  currentTooltip.style.top = `${y}px`;
}

function hideTooltip() {
  if (currentTooltip) currentTooltip.style.display = "none";
}

function esc(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function formatDateRange(start, end) {
  if (!start && !end) return "";
  const s = start ? new Date(start).toLocaleDateString(undefined, { month: "short", year: "numeric" }) : "";
  const e = end ? new Date(end).toLocaleDateString(undefined, { month: "short", year: "numeric" }) : "present";
  return s && e ? `${s} \u2013 ${e}` : s || e;
}
