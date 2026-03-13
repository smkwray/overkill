const DEFAULT_TAB = "chart";
const ROUTE_KEYS = ["tab", "bundle", "episode", "metric", "source", "scope", "layer"];

export function readRoute() {
  const hash = window.location.hash.replace(/^#/, "");
  const params = new URLSearchParams(hash);

  return {
    tab: params.get("tab") || DEFAULT_TAB,
    bundle: params.get("bundle"),
    episode: params.get("episode"),
    metric: params.get("metric"),
    source: params.get("source"),
    scope: params.get("scope") || "episode",
    layer: params.get("layer") || "core",
  };
}

export function buildRoute({ tab, bundle, episode, metric, source, scope, layer }) {
  const params = new URLSearchParams();

  if (tab && tab !== DEFAULT_TAB) params.set("tab", tab);
  if (bundle) params.set("bundle", bundle);
  if (episode) params.set("episode", episode);
  if (metric) params.set("metric", metric);
  if (source) params.set("source", source);
  if (scope && scope !== "episode") params.set("scope", scope);
  if (layer && layer !== "core") params.set("layer", layer);

  const text = params.toString();
  return text ? `#${text}` : "#";
}

export function sameRoute(nextRoute) {
  const current = readRoute();
  return ROUTE_KEYS.every((key) => (current[key] || "") === (nextRoute[key] || ""));
}
