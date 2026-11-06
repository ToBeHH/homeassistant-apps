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

function source(region) {
  return {
    type: "vector",
    url: `pmtiles://${abs(`tiles/${encodeURIComponent(region.file)}`)}`,
    attribution:
      '<a href="https://protomaps.com">Protomaps</a> © <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>',
  };
}

// The world map, if there is one, lies under the region and fills the rest of the
// screen. The region's land and water are opaque, so it hides what is below.
function style(region, world) {
  const flavor = dark ? "dark" : "light";
  const layers = (name) => basemaps.layers(name, basemaps.namedFlavor(flavor), { lang });
  const under = world && world !== region;
  return {
    version: 8,
    // Appended, not resolved: URL() would percent-encode the {tokens}.
    glyphs: `${abs("fonts/")}{fontstack}/{range}.pbf`,
    sprite: abs(`sprites/v4/${flavor}`),
    sources: {
      protomaps: source(region),
      ...(under ? { world: source(world) } : {}),
    },
    layers: under
      ? [
          ...layers("world").map((l) => ({ ...l, id: `world-${l.id}` })),
          ...layers("protomaps").filter((l) => l.type !== "background"),
        ]
      : layers("protomaps"),
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
  const world = regions.find((r) => r.label === "world");
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
    style: style(current, world),
    bounds: current.bbox,
    maxZoom: 20,
    hash: true,
    attributionControl: { compact: true },
  });
  map.addControl(new maplibregl.NavigationControl(), "top-right");
  map.addControl(new maplibregl.ScaleControl(), "bottom-left");

  select.addEventListener("change", () => {
    current = regions.find((r) => r.label === select.value);
    remember(current.label);
    map.setStyle(style(current, world));
    map.fitBounds(current.bbox, { animate: false });
  });

  // --- Place search ------------------------------------------------------------

  const ZOOM = { region: 7, place: 12, postcode: 13, water: 11, mountain: 13, road: 16 };
  const input = document.getElementById("search");
  const list = document.getElementById("results");
  let marker = null;
  let timer = null;
  let asked = 0;

  const covers = (r, lat, lon) =>
    lon >= r.bbox[0] && lon <= r.bbox[2] && lat >= r.bbox[1] && lat <= r.bbox[3];

  function note(text) {
    const li = document.createElement("li");
    li.className = "note";
    li.textContent = text;
    list.append(li);
  }

  function go(hit) {
    list.hidden = true;
    if (!covers(current, hit.lat, hit.lon)) {
      const region = regions.find((r) => covers(r, hit.lat, hit.lon));
      if (!region) {
        list.hidden = false;
        list.replaceChildren();
        note(`${hit.name} is outside your map regions.`);
        return;
      }
      current = region;
      select.value = region.label;
      remember(region.label);
      map.setStyle(style(region, world));
    }
    if (marker) marker.remove();
    marker = new maplibregl.Marker().setLngLat([hit.lon, hit.lat]).addTo(map);
    map.jumpTo({ center: [hit.lon, hit.lat], zoom: ZOOM[hit.kind] || 17 });
  }

  async function find(query) {
    const ticket = ++asked;
    let hits = [];
    let failed = false;
    try {
      const r = await fetch(`../control/places?q=${encodeURIComponent(query)}`);
      hits = (await r.json()).results;
    } catch {
      failed = true;
    }
    if (ticket !== asked) return;
    list.replaceChildren();
    for (const hit of hits) {
      const b = document.createElement("button");
      b.type = "button";
      const where = [hit.kind, hit.near, hit.country].filter(Boolean).join(", ");
      const small = document.createElement("small");
      small.textContent = where;
      b.append(hit.name, document.createElement("br"), small);
      b.addEventListener("click", () => go(hit));
      const li = document.createElement("li");
      li.append(b);
      list.append(li);
    }
    if (failed) note("The search is not available right now.");
    else if (!hits.length) note("Nothing found. Is place_search on in the app configuration?");
    else note("Places: GeoNames (CC BY 4.0), streets: OpenStreetMap");
    list.hidden = false;
  }

  input.addEventListener("input", () => {
    clearTimeout(timer);
    const query = input.value.trim();
    if (query.length < 2) {
      asked++;
      list.hidden = true;
      return;
    }
    timer = setTimeout(() => find(query), 250);
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") list.hidden = true;
    if (e.key === "Enter") {
      const first = list.querySelector("button");
      if (first) first.click();
    }
  });
}
