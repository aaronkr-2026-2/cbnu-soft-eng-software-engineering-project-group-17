"use strict";

/* SleepInsight web interface.
 * Plain JavaScript, no build step. All text that comes from the server is
 * inserted with textContent / append(string) (never innerHTML), so data from
 * an imported file can never run as code in the page.
 */

const STAGE_LEVEL = { deep: 0, light: 1, rem: 2, wake: 3 };
const STAGE_LABEL = ["Deep", "Light", "REM", "Awake"];

let nights = [];      // night summaries, oldest first
let current = null;   // the full night being shown
const charts = {};    // Chart.js instances by canvas id

const $ = (id) => document.getElementById(id);

// ---------- small helpers ----------------------------------------------------

/** Create an element: h("p", {class: "muted"}, "text", childNode) */
function h(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  node.append(...children);
  return node;
}

function clear(node) {
  node.replaceChildren();
  return node;
}

function setStatus(message, isError = false) {
  const el = $("status");
  el.textContent = message;
  el.className = isError ? "error" : "";
}

async function request(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (body.detail) message = body.detail.map((d) => `${d.loc.slice(1).join(".")}: ${d.msg}`).join("; ");
    } catch (_) { /* response had no JSON body */ }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

/** Run an async action, showing progress and errors in the status line. */
async function run(button, message, action) {
  if (button) button.disabled = true;
  setStatus(message);
  try {
    await action();
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    if (button) button.disabled = false;
  }
}

function timeOf(iso) { return iso.slice(11, 16); }

/** Date -> "YYYY-MM-DDTHH:MM" in local time, the format <input type="datetime-local"> expects. */
function toLocalInput(date) {
  const p = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}T${p(date.getHours())}:${p(date.getMinutes())}`;
}
function minutesToText(min) { return `${Math.floor(min / 60)} h ${String(Math.round(min % 60)).padStart(2, "0")} min`; }
function show(value, unit = "") { return value === null || value === undefined ? "n/a" : `${value}${unit}`; }

function drawChart(id, config) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart($(id), config);
  return charts[id];
}

// ---------- loading ----------------------------------------------------------------

async function loadAll(selectId = null) {
  nights = await request("/api/nights");
  const hasData = nights.length > 0;
  $("empty").hidden = hasData;
  $("dashboard").hidden = !hasData;
  if (!hasData) { setStatus(""); return; }

  Chart.defaults.color = getComputedStyle(document.body).color;
  Chart.defaults.borderColor = getComputedStyle(document.body).getPropertyValue("--line");

  renderTrend();
  const select = clear($("night-select"));
  [...nights].reverse().forEach((n) => select.append(h("option", { value: n.id }, `${n.night_date}  -  score ${n.summary.score}`)));
  const id = selectId || nights[nights.length - 1].id;
  select.value = id;
  await Promise.all([showNight(id), loadForecast(), loadInsights()]);
  setStatus(`${nights.length} night${nights.length === 1 ? "" : "s"} loaded.`);
}

async function showNight(id) {
  current = await request(`/api/nights/${id}`);
  renderSummary(current);
  renderHypnogram(current);
  renderVitals(current);
  // Default alarm window: the 30 minutes before the final awakening.
  const endText = current.summary.final_wake_time || current.end;
  $("alarm-end").value = endText;
  $("alarm-start").value = toLocalInput(new Date(new Date(`${endText}:00`).getTime() - 30 * 60000));
  clear($("alarm-result"));
  $("ctx-date").value = current.night_date;
}

// ---------- rendering: overview ------------------------------------------------------

function renderTrend() {
  drawChart("chart-trend", {
    data: {
      labels: nights.map((n) => n.night_date.slice(5)),
      datasets: [
        { type: "bar", label: "Sleep score", data: nights.map((n) => n.summary.score), backgroundColor: "#748ffc", yAxisID: "y" },
        { type: "line", label: "Sleep (h)", data: nights.map((n) => +(n.summary.total_sleep_min / 60).toFixed(1)), borderColor: "#f08c00", pointRadius: 2, yAxisID: "y1" },
      ],
    },
    options: {
      maintainAspectRatio: false,
      scales: {
        y: { min: 0, max: 100, title: { display: true, text: "Score" } },
        y1: { position: "right", min: 0, max: 12, grid: { drawOnChartArea: false }, title: { display: true, text: "Hours" } },
      },
    },
  });
}

async function loadForecast() {
  const data = await request("/api/forecast");
  const box = clear($("forecast"));
  if (data.energy_score === null) { box.append(h("p", { class: "muted" }, data.note)); return; }
  box.append(
    h("div", {}, h("span", { class: "big-number" }, String(data.energy_score)), h("span", { class: "pill" }, `${data.label} energy`)),
    h("p", { class: "muted small" }, `For ${data.for_date}, based on night ${data.based_on_night} and ${data.nights_used} recent night(s). Confidence: ${data.confidence}.`),
  );
  data.components.forEach((c) => {
    box.append(barRow(c.name, c.value, c.detail));
  });
  box.append(h("p", { class: "muted small" }, data.note));
}

function barRow(label, value, detail) {
  const row = h("div", { class: "bar-row", title: detail || "" },
    h("span", {}, label),
    h("div", { class: "bar" }, h("span", { style: `width:${Math.max(0, Math.min(100, value))}%` })),
    h("span", {}, String(value)),
  );
  return row;
}

// ---------- rendering: one night -------------------------------------------------------

function renderSummary(night) {
  const s = night.summary;
  const tiles = [
    ["Sleep score", show(s.score), "score"],
    ["Time asleep", minutesToText(s.total_sleep_min)],
    ["Efficiency", `${Math.round(s.efficiency * 100)}%`],
    ["Fell asleep after", `${s.sleep_latency_min} min`],
    ["Awake during night", `${s.waso_min} min (${s.awakenings}x)`],
    ["Deep sleep", `${s.deep_min} min (${s.deep_pct}%)`],
    ["REM sleep", `${s.rem_min} min (${s.rem_pct}%)`],
    ["Light sleep", `${s.light_min} min (${s.light_pct}%)`],
    ["Average heart rate", show(s.avg_hr, " bpm")],
    ["Lowest 5-min heart rate", show(s.min_hr_5min, " bpm")],
    ["Average HRV (RMSSD)", show(s.avg_hrv, " ms")],
    ["Lowest SpO2", show(s.spo2_min, "%"), s.spo2_attention ? "attention" : ""],
    ["Desaturations per hour", show(s.odi), s.spo2_attention ? "attention" : ""],
  ];
  const box = clear($("tiles"));
  tiles.forEach(([label, value, kind]) => {
    box.append(h("div", { class: `tile ${kind || ""}` }, h("div", { class: "value" }, value), h("div", { class: "label" }, label)));
  });

  const method = night.stage_method === "ml"
    ? "Sleep stages estimated by the machine-learning model (trained on simulated data)."
    : "Sleep stages estimated by simple rules (the file lacks HRV or movement data).";
  const source = night.source === "synthetic" ? " This night is synthetic demo data." : "";
  const warning = s.spo2_attention ? " Repeated oxygen dips were detected; this is not a diagnosis (see Recommendations)." : "";
  $("method-note").textContent = method + source + warning;

  const breakdown = clear($("breakdown"));
  Object.entries(s.score_breakdown).forEach(([name, value]) => breakdown.append(barRow(name, value)));
}

function renderHypnogram(night) {
  const labels = night.epochs.map((e) => timeOf(e.t));
  drawChart("chart-hypno", {
    type: "line",
    data: {
      labels,
      datasets: [{ label: "Stage", data: night.epochs.map((e) => STAGE_LEVEL[e.stage]), stepped: true, borderColor: "#748ffc", borderWidth: 2, pointRadius: 0, fill: false }],
    },
    options: {
      maintainAspectRatio: false,
      animation: false,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          min: -0.2,
          max: 3.2,
          // One tick per stage: without this Chart.js puts ticks at -0.2, 0.8, ... and the labels disappear.
          afterBuildTicks: (axis) => { axis.ticks = [0, 1, 2, 3].map((value) => ({ value })); },
          ticks: { callback: (v) => STAGE_LABEL[v] || "" },
        },
        x: { ticks: { maxTicksLimit: 10 } },
      },
    },
  });
}

function renderVitals(night) {
  const labels = night.epochs.map((e) => timeOf(e.t));
  const datasets = [{ label: "Heart rate (bpm)", data: night.epochs.map((e) => e.hr), borderColor: "#fa5252", pointRadius: 0, borderWidth: 1.5, yAxisID: "y" }];
  const scales = { y: { title: { display: true, text: "bpm" } }, x: { ticks: { maxTicksLimit: 10 } } };
  if (night.epochs.some((e) => e.spo2 !== undefined && e.spo2 !== null)) {
    datasets.push({ label: "SpO2 (%)", data: night.epochs.map((e) => e.spo2 ?? null), borderColor: "#339af0", pointRadius: 0, borderWidth: 1.5, yAxisID: "y1" });
    scales.y1 = { position: "right", min: 82, max: 100, grid: { drawOnChartArea: false }, title: { display: true, text: "%" } };
  }
  drawChart("chart-vitals", { type: "line", data: { labels, datasets }, options: { maintainAspectRatio: false, animation: false, scales } });
}

// ---------- smart alarm -----------------------------------------------------------------

function markAlarmOnChart(result) {
  const chart = charts["chart-hypno"];
  const labels = current.epochs.map((e) => e.t);
  const point = (time, color, label) => {
    const index = labels.indexOf(time);
    return {
      type: "line", label, showLine: false, pointRadius: 9, pointStyle: "rectRot", backgroundColor: color, borderColor: color,
      data: labels.map((_, i) => (i === index ? STAGE_LEVEL[current.epochs[i].stage] : null)),
    };
  };
  chart.data.datasets = chart.data.datasets.slice(0, 1);
  chart.data.datasets.push(point(result.smart_alarm.time, "#2f9e44", "Smart alarm"), point(result.fixed_alarm.time, "#e8590c", "Fixed alarm"));
  chart.options.plugins.legend.display = true;
  chart.update();
}

function alarmBox(title, alarm) {
  const where = alarm.stage === "wake" ? "while awake" : `in ${alarm.stage} sleep`;
  return h("div", { class: "tile" }, h("div", { class: "label" }, title), h("div", { class: "value" }, timeOf(alarm.time)), h("div", {}, where));
}

async function simulateAlarm(event) {
  event.preventDefault();
  const body = { window_start: $("alarm-start").value, window_end: $("alarm-end").value };
  const result = await request(`/api/nights/${current.id}/smart-alarm`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const box = clear($("alarm-result"));
  box.append(
    h("div", { class: "compare" }, alarmBox("Smart alarm rings at", result.smart_alarm), alarmBox("A fixed alarm would ring at", result.fixed_alarm)),
    h("p", {}, `${result.reason} ${result.minutes_earlier > 0 ? `That is ${result.minutes_earlier} minute(s) before the end of the window.` : ""}`),
    h("p", { class: "muted small" }, result.note),
  );
  markAlarmOnChart(result);
  setStatus("");
}

// ---------- insights --------------------------------------------------------------------

async function loadInsights() {
  const data = await request("/api/insights");
  const corr = clear($("correlations"));
  if (data.correlations.length === 0) {
    corr.append(h("p", { class: "muted" }, "Not enough data yet: correlations need at least 7 nights with daily context."));
  } else {
    const body = h("tbody");
    data.correlations.forEach((c) => body.append(h("tr", {},
      h("td", {}, c.label), h("td", {}, c.r.toFixed(2)), h("td", {}, String(c.n)), h("td", {}, c.p.toFixed(3)),
      h("td", {}, `${c.strength}, ${c.direction}`))));
    corr.append(h("table", {}, h("thead", {}, h("tr", {}, ...["Factor", "r", "Nights", "p", "Relation to sleep score"].map((t) => h("th", {}, t)))), body));
  }
  $("disclaimer").textContent = data.disclaimer;

  const recs = clear($("recommendations"));
  data.recommendations.forEach((r) => recs.append(h("div", { class: "rec" },
    h("h3", {}, r.title, h("span", { class: `pill ${r.level}` }, r.level)),
    h("p", {}, r.text), h("p", { class: "evidence" }, r.evidence))));
}

// ---------- user actions --------------------------------------------------------------------

$("btn-demo").addEventListener("click", (e) => run(e.currentTarget, "Generating demo nights...", async () => {
  await request("/api/demo/seed", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nights: 28 }) });
  await loadAll();
}));

$("btn-clear").addEventListener("click", (e) => run(e.currentTarget, "Removing demo data...", async () => {
  const result = await request("/api/demo", { method: "DELETE" });
  await loadAll();
  setStatus(`Removed ${result.nights_deleted} synthetic night(s).`);
}));

$("file-import").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  e.target.value = "";  // allows choosing the same file again
  if (!file) return;
  await run(null, `Importing ${file.name}...`, async () => {
    const form = new FormData();
    form.append("file", file);
    const result = await request("/api/nights/import", { method: "POST", body: form });
    await loadAll(result.id);
    const notes = [result.replaced_existing ? "Replaced the existing night with the same date." : "", ...result.warnings].filter(Boolean);
    setStatus(`Imported night ${result.night_date}. ${notes.join(" ")}`);
  });
});

$("night-select").addEventListener("change", (e) => run(null, "Loading night...", async () => { await showNight(e.target.value); setStatus(""); }));
$("alarm-form").addEventListener("submit", (e) => run(null, "Simulating...", () => simulateAlarm(e)));

$("context-form").addEventListener("submit", (e) => {
  e.preventDefault();
  run(null, "Saving...", async () => {
    const body = {};
    const number = (id, key) => { const v = $(id).value; if (v !== "") body[key] = Number(v); };
    number("ctx-steps", "steps"); number("ctx-caffeine", "caffeine_cups"); number("ctx-alcohol", "alcohol_units"); number("ctx-stress", "stress");
    body.late_workout = $("ctx-workout").checked;
    await request(`/api/context/${$("ctx-date").value}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    await loadInsights();
    setStatus(`Saved context for ${$("ctx-date").value}.`);
  });
});

$("model-details").addEventListener("toggle", async (e) => {
  if (!e.target.open || $("model-info").textContent) return;
  try { $("model-info").textContent = JSON.stringify(await request("/api/model-info"), null, 2); }
  catch (error) { $("model-info").textContent = error.message; }
});

run(null, "Loading...", loadAll);
