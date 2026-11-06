// Landing page: reads status.json (downloader), info.json and the library
// list. All URLs are relative, so the page works under the ingress prefix.
"use strict";

const STATES = {
  starting: ["Starting", "busy"],
  checking: ["Checking for updates", "busy"],
  downloading: ["Downloading", "busy"],
  waiting_for_window: ["Waiting for download window", "warn"],
  waiting_for_storage: ["No storage location", "warn"],
  idle: ["Idle", "ok"],
  error: ["Error", "err"],
};

const ITEM_STATES = {
  current: "Up to date",
  queued: "Queued",
  downloading: "Downloading",
  paused: "Paused",
  error: "Failed",
  unknown: "Not in the Kiwix catalog",
  no_space: "Not enough space",
  no_memory: "Not enough memory",
};

const ITEM_ORDER = ["downloading", "paused", "queued", "error", "no_space", "no_memory", "unknown", "current"];

const $ = (sel) => document.querySelector(sel);

function bytes(n) {
  if (n == null) return "–";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1000 && i < units.length - 1) { n /= 1000; i++; }
  return `${n.toFixed(n < 10 && i > 0 ? 1 : 0)} ${units[i]}`;
}

function when(iso) {
  if (!iso) return "–";
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString();
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v; else node.setAttribute(k, v);
  }
  for (const c of children) if (c != null) node.append(c);
  return node;
}

async function getJSON(url) {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

function showAlert(text, error) {
  const a = $("#alert");
  a.hidden = !text;
  a.textContent = text || "";
  a.classList.toggle("error", !!error);
}

function renderLibrary(info, list) {
  const summary = $("#library-summary");
  const action = $("#library-action");
  action.replaceChildren();
  if (list) {
    const n = list.length;
    const size = list.reduce((s, z) => s + (z.size_bytes || 0), 0);
    summary.textContent = n ? `${n} source${n === 1 ? "" : "s"}, ${bytes(size)}` : "No content yet.";
  } else {
    summary.textContent = "The library server is starting…";
  }
  if (info && info.library_port) {
    const url = `http://${location.hostname}:${info.library_port}/`;
    action.append(el("a", { class: "button", href: url, target: "_blank", rel: "noopener" }, "Open library"));
  } else {
    action.append(el("span", { class: "muted" },
      "To open the library, set a port for 8899/tcp under Network in the app settings."));
  }
}

function renderStatus(st) {
  const [label, kind] = STATES[st.state] || [st.state, ""];
  const badge = $("#state");
  badge.textContent = label;
  badge.className = `badge ${kind}`;

  if (st.state === "waiting_for_storage") {
    showAlert(`${st.message}. Set a storage location (data_path) in the app configuration; nothing is downloaded until then.`);
  } else if (st.state === "error") {
    showAlert(st.message, true);
  } else {
    showAlert("");
  }

  const s = st.storage;
  $("#storage").textContent = s ? `${s.path} – ${bytes(s.free)} free of ${bytes(s.total)}` : "–";
  const bar = $("#storage-bar");
  bar.hidden = !s;
  if (s && s.total) {
    const used = 1 - s.free / s.total;
    bar.firstElementChild.style.width = `${(used * 100).toFixed(1)}%`;
    bar.classList.toggle("high", used > 0.9);
  }
  $("#last-check").textContent = when(st.last_check);
  $("#last-success").textContent = when(st.last_success);
  $("#next-check").textContent = when(st.next_check);

  const items = Object.entries(st.items || {}).sort(([ka, a], [kb, b]) =>
    (ITEM_ORDER.indexOf(a.state) - ITEM_ORDER.indexOf(b.state)) || ka.localeCompare(kb));
  $("#items").hidden = !items.length;
  $("#items-empty").hidden = !!items.length || st.state === "waiting_for_storage";
  const rows = items.map(([key, it]) => {
    const status = el("td", {}, ITEM_STATES[it.state] || it.state);
    if ((it.state === "downloading" || it.state === "paused") && it.size) {
      const pct = Math.min(100, (100 * (it.done || 0)) / it.size);
      const b = el("div", { class: "bar" }, el("span"));
      b.firstElementChild.style.width = `${pct.toFixed(1)}%`;
      status.append(` ${pct.toFixed(0)} %`, b);
    }
    if (it.message) status.append(el("div", { class: "msg" }, it.message));
    const name = it.kind === "map" ? `Map: ${it.title || key.slice(4)}` : (it.title || key);
    return el("tr", {},
      el("td", {}, name, el("div", { class: "file" }, it.file || key)),
      el("td", { class: "size" }, it.size ? bytes(it.size) : "–"),
      status);
  });
  $("#items tbody").replaceChildren(...rows);
}

function renderMaps(index) {
  const regions = Object.values((index && index.regions) || {});
  const size = regions.reduce((s, r) => s + (r.size || 0), 0);
  $("#maps-summary").textContent = regions.length
    ? `${regions.length} region${regions.length === 1 ? "" : "s"}, ${bytes(size)}`
    : "No maps yet.";
}

// --- MCP access ---------------------------------------------------------------

const CONTROL_HEADERS = { "X-Requested-By": "start-page" };
let mcpToken = "";
let mcpShown = false;
let renewArmed = null;

function mcpUrl(info) {
  return info && info.mcp_port ? `http://${location.hostname}:${info.mcp_port}/mcp` : "";
}

function renderMcpToken() {
  $("#mcp-token").textContent = mcpShown ? mcpToken : "••••••••••••••••";
  $("#mcp-show").textContent = mcpShown ? "Hide" : "Show";
}

// navigator.clipboard is missing on plain HTTP and blocked in some iframes.
async function copy(text, what) {
  let done = false;
  try {
    await navigator.clipboard.writeText(text);
    done = true;
  } catch {
    const area = el("textarea");
    area.value = text;
    document.body.append(area);
    area.select();
    try { done = document.execCommand("copy"); } catch { /* handled below */ }
    area.remove();
  }
  $("#mcp-note").textContent = done ? `${what} copied.` : "Copying failed, please select it by hand.";
  if (!done) { mcpShown = true; renderMcpToken(); }
}

async function loadMcp(info) {
  const url = mcpUrl(info);
  $("#mcp-off").hidden = !!url;
  $("#mcp-url").textContent = url || "–";
  $("#mcp-copy-cmd").disabled = !url;
  $("#mcp-summary").textContent = url ? "Running." : "Off: no port set.";
  try {
    mcpToken = (await getJSON("control/mcp-token")).token;
  } catch {
    $("#mcp-note").textContent = "The token is not available yet, please reload in a minute.";
  }
  renderMcpToken();

  $("#mcp-show").onclick = () => { mcpShown = !mcpShown; renderMcpToken(); };
  $("#mcp-copy").onclick = () => copy(mcpToken, "Token");
  $("#mcp-copy-cmd").onclick = () => copy(
    `claude mcp add --transport http offline-knowledge ${url} --header "Authorization: Bearer ${mcpToken}"`,
    "Command",
  );
  $("#mcp-renew").onclick = async () => {
    const button = $("#mcp-renew");
    if (!renewArmed) {
      button.textContent = "Really? Connected assistants lose access";
      renewArmed = setTimeout(() => { renewArmed = null; button.textContent = "Recreate token"; }, 6000);
      return;
    }
    clearTimeout(renewArmed);
    renewArmed = null;
    button.textContent = "Recreate token";
    const r = await fetch("control/mcp-token", { method: "POST", headers: CONTROL_HEADERS });
    if (r.ok) {
      mcpToken = (await r.json()).token;
      $("#mcp-note").textContent = "New token created. Update it in your assistants.";
      renderMcpToken();
    } else {
      $("#mcp-note").textContent = "Creating a new token failed.";
    }
  };
}

$("#update-now").onclick = async () => {
  const button = $("#update-now");
  button.disabled = true;
  const r = await fetch("control/update", { method: "POST", headers: CONTROL_HEADERS }).catch(() => null);
  button.textContent = r && r.ok ? "Requested" : "Failed";
  setTimeout(() => { button.disabled = false; button.textContent = "Check now"; }, 8000);
};

async function refresh() {
  const [info, status, list, maps] = await Promise.allSettled([
    getJSON("info.json"), getJSON("status.json"), getJSON("library/list"),
    getJSON("maps/tiles/index.json"),
  ]);
  renderMaps(maps.status === "fulfilled" ? maps.value : null);
  if (info.status === "fulfilled") $("#version").textContent = `Version ${info.value.version}`;
  renderLibrary(info.value, list.status === "fulfilled" ? list.value : null);
  if (status.status === "fulfilled") {
    renderStatus(status.value);
  } else {
    $("#state").textContent = "Starting";
    $("#state").className = "badge busy";
  }
}

refresh();
setInterval(refresh, 10000);
getJSON("info.json").then(loadMcp, () => loadMcp(null));
