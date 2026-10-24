// Offline map viewer: MapLibre + PMTiles + Protomaps basemap style, with all
// fonts and sprites served locally. Regions come from tiles/index.json, which
// the downloader writes next to the .pmtiles files.
import * as maplibregl from "./lib/maplibre-gl.mjs";

/* global pmtiles, basemaps */

// MapLibre needs absolute URLs; build them from this page so the viewer works
// under the Home Assistant ingress prefix too.
const abs = (path) => new URL(path, location.href).href;
const dark = matchMedia("(prefers-color-scheme: dark)").matches;
const lang = (navigator.language || "en").slice(0, 2);
const STORE = "okdl-map-region";

const protocol = new pmtiles.Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);

function style(region) {
  const flavor = dark ? "dark" : "light";
  return {
    version: 8,
    // Appended, not resolved: URL() would percent-encode the {tokens}.
    glyphs: `${abs("fonts/")}{fontstack}/{range}.pbf`,
    sprite: abs(`sprites/v4/${flavor}`),
    sources: {
      protomaps: {
        type: "vector",
        url: `pmtiles://${abs(`tiles/${encodeURIComponent(region.file)}`)}`,
        attribution:
          '<a href="https://protomaps.com">Protomaps</a> © <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>',
      },
    },
    layers: basemaps.layers("protomaps", basemaps.namedFlavor(flavor), { lang }),
  };
}

async function loadRegions() {
  try {
    const r = await fetch("tiles/index.json", { cache: "no-store" });
    if (!r.ok) return [];
    const index = await r.json();
    return Object.entries(index.regions || {})
      .map(([label, v]) => ({ label, ...v }))
      // Most detailed first: that is usually the one people want.
      .sort((a, b) => b.maxzoom - a.maxzoom || a.label.localeCompare(b.label));
  } catch {
    return [];
  }
}

function remembered() {
  try { return localStorage.getItem(STORE); } catch { return null; }
}

function remember(label) {
  try { localStorage.setItem(STORE, label); } catch { /* private mode */ }
}

const regions = await loadRegions();
if (!regions.length) {
  document.getElementById("empty").hidden = false;
} else {
  let current = regions.find((r) => r.label === remembered()) || regions[0];
  const select = document.getElementById("region");
  for (const r of regions) {
    const opt = document.createElement("option");
    opt.value = r.label;
    opt.textContent = r.title || r.label;
    select.append(opt);
  }
  select.value = current.label;
  select.hidden = regions.length < 2;

  const map = new maplibregl.Map({
    container: "map",
    style: style(current),
    bounds: current.bbox,
    maxZoom: 19,
    hash: true,
    attributionControl: { compact: true },
  });
  map.addControl(new maplibregl.NavigationControl(), "top-right");
  map.addControl(new maplibregl.ScaleControl(), "bottom-left");

  select.addEventListener("change", () => {
    current = regions.find((r) => r.label === select.value);
    remember(current.label);
    map.setStyle(style(current));
    map.fitBounds(current.bbox, { animate: false });
  });
}
