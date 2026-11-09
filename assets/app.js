"use strict";

const STATUS_KEY = "global-ai-career-tracker-statuses-v1";
const STATUS_OPTIONS = ["new", "reviewing", "applied", "interviewing", "offer", "archived"];
const MAX_BREAKDOWN = { role_blend: 30, travel: 20, compensation: 20, visa: 15, skill_seniority: 10, freshness_source: 5 };
const state = { jobs: [], report: null, config: null, statuses: loadStatuses() };

function loadStatuses() {
  try { return JSON.parse(localStorage.getItem(STATUS_KEY) || "{}"); }
  catch { return {}; }
}
function saveStatuses() { localStorage.setItem(STATUS_KEY, JSON.stringify(state.statuses)); }
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function statusFor(job) { return state.statuses[job.id] || "new"; }
function formatDate(value) {
  if (!value) return "date not supplied";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}
function visaLabel(value) {
  return { sponsored: "Visa sponsorship stated", supported: "Immigration support stated", unknown: "Visa needs validation", not_supported: "Sponsorship not supported" }[value] || "Visa needs validation";
}
function compensationLabel(job) {
  if (job.score?.compensation_status === "below_target") return "Verified ceiling below €120k";
  const compensation = job.compensation;
  if (!compensation) return "Compensation needs validation";
  return `${compensation.currency} ${Number(compensation.min || 0).toLocaleString()}–${Number(compensation.max).toLocaleString()}`;
}
function matches(job) {
  const search = document.querySelector("#search").value.trim().toLowerCase();
  const haystack = [job.title, job.company, ...(job.locations || [])].join(" ").toLowerCase();
  return (!search || haystack.includes(search))
    && (!document.querySelector("#company-filter").value || job.company === document.querySelector("#company-filter").value)
    && (!document.querySelector("#visa-filter").value || job.visa_status === document.querySelector("#visa-filter").value)
    && (!document.querySelector("#status-filter").value || statusFor(job) === document.querySelector("#status-filter").value)
    && (!document.querySelector("#remote-only").checked || job.remote)
    && (job.score.total >= Number(document.querySelector("#min-score").value))
    && (document.querySelector("#include-rejected").checked || !job.score.hard_reject);
}
function breakdownNode(job) {
  const wrap = el("div", "breakdown");
  Object.entries(job.score.breakdown).forEach(([name, value]) => {
    const row = el("div", "breakdown-row");
    row.append(el("span", "", name.replaceAll("_", " ")));
    const bar = el("span", "bar");
    const fill = el("span");
    fill.style.width = `${Math.round((value / MAX_BREAKDOWN[name]) * 100)}%`;
    bar.append(fill);
    row.append(bar, el("strong", "", String(value)));
    wrap.append(row);
  });
  return wrap;
}
function jobCard(job) {
  const card = el("article", "job-card");
  card.dataset.jobId = job.id;
  const main = el("div", "job-main");
  main.append(el("div", "score", String(job.score.total)));
  const body = el("div");
  body.append(el("h3", "job-title", job.title));
  body.append(el("p", "job-meta", `${job.company} · ${(job.locations || []).join(" / ") || "Location not supplied"} · ${formatDate(job.posted_at)}`));
  const badges = el("div", "badges");
  badges.append(el("span", "badge visa", visaLabel(job.visa_status)));
  badges.append(el("span", "badge", job.travel_percent == null ? "Travel needs validation" : `${job.travel_percent}% travel stated`));
  badges.append(el("span", job.score.compensation_status === "below_target" ? "badge error" : "badge warning", compensationLabel(job)));
  if (job.stale) badges.append(el("span", "badge error", "Stale · source unavailable"));
  body.append(badges);
  main.append(body);

  const actions = el("div", "job-actions");
  const select = el("select");
  select.setAttribute("aria-label", `Pipeline status for ${job.title}`);
  STATUS_OPTIONS.forEach(value => {
    const option = el("option", "", value[0].toUpperCase() + value.slice(1));
    option.value = value;
    option.selected = statusFor(job) === value;
    select.append(option);
  });
  select.addEventListener("change", () => { state.statuses[job.id] = select.value; saveStatuses(); render(); });
  const link = el("a", "official-link", "Open official role ↗");
  link.href = job.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  actions.append(select, link);
  main.append(actions);
  card.append(main);

  const details = el("details", "job-details");
  details.append(el("summary", "", "Evidence & score breakdown"));
  const grid = el("div", "detail-grid");
  const evidence = el("div");
  evidence.append(el("h4", "", "Visa evidence"), el("p", "", job.visa_evidence || "No explicit visa language found in the official listing."));
  evidence.append(el("h4", "", "Official excerpt"), el("p", "", job.description_excerpt || "No excerpt supplied by the source."));
  const scoring = el("div");
  scoring.append(el("h4", "", `Fit score · ${job.score.total}/100`), breakdownNode(job));
  grid.append(evidence, scoring);
  details.append(grid);
  card.append(details);
  return card;
}
function filteredJobs() { return state.jobs.filter(matches); }
function render() {
  const jobs = filteredJobs();
  const list = document.querySelector("#jobs");
  list.replaceChildren();
  if (!jobs.length) list.append(el("div", "empty", "No roles match these filters. Reset filters or lower the score threshold."));
  else jobs.forEach(job => list.append(jobCard(job)));
  document.querySelector("#visible-count").textContent = String(jobs.length);
  document.querySelector("#result-summary").textContent = `${jobs.length} of ${state.jobs.length} roles`;
}
function renderSources() {
  const wrap = document.querySelector("#source-health");
  wrap.replaceChildren();
  if (!state.report?.sources?.length) { wrap.textContent = "No refresh report available."; return; }
  state.report.sources.forEach(source => {
    const text = source.status === "ok" ? `${source.company} · ${source.jobs}` : `${source.company} · error`;
    const pill = el("span", `source-pill ${source.status}`, text);
    if (source.error) pill.title = source.error;
    wrap.append(pill);
  });
}
function populateConfig() {
  const company = document.querySelector("#company-filter");
  [...new Set(state.jobs.map(job => job.company))].sort().forEach(name => {
    const option = el("option", "", name); option.value = name; company.append(option);
  });
  const questions = document.querySelector("#travel-questions");
  (state.config.travel_recruiter_questions || []).forEach(question => questions.append(el("li", "", question)));
}
function csvCell(value) { return `"${String(value ?? "").replaceAll('"', '""')}"`; }
function safeUrl(url) { return /^https:\/\//.test(url || "") ? url : ""; }
function exportCsv() {
  const headers = ["company", "title", "locations", "score", "pipeline_status", "visa_status", "visa_evidence", "travel_percent", "compensation_status", "raw_url", "spreadsheet_link"];
  const rows = filteredJobs().map(job => {
    const raw = safeUrl(job.url);
    const spreadsheet = raw ? `=HYPERLINK("${raw.replaceAll('"', '""')}","Open official role")` : "";
    return [job.company, job.title, (job.locations || []).join(" | "), job.score.total, statusFor(job), job.visa_status, job.visa_evidence, job.travel_percent, job.score.compensation_status, raw, spreadsheet];
  });
  const csv = [headers.map(csvCell).join(","), ...rows.map(row => row.map(csvCell).join(","))].join("\r\n");
  const blob = new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob); link.download = "global-ai-career-tracker.csv"; link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 0);
}
function resetFilters() {
  ["#search", "#company-filter", "#visa-filter", "#status-filter"].forEach(selector => { document.querySelector(selector).value = ""; });
  document.querySelector("#min-score").value = "0";
  document.querySelector("#min-score-value").value = "0";
  document.querySelector("#remote-only").checked = false;
  document.querySelector("#include-rejected").checked = false;
  render();
}
async function start() {
  try {
    const [dataResponse, reportResponse, configResponse] = await Promise.all([
      fetch("data/jobs.json"), fetch("data/refresh-report.json"), fetch("config/tracker.json")
    ]);
    if (!dataResponse.ok || !configResponse.ok) throw new Error("Required generated data is unavailable");
    const data = await dataResponse.json();
    state.jobs = data.jobs || [];
    state.config = await configResponse.json();
    state.report = reportResponse.ok ? await reportResponse.json() : null;
    document.querySelector("#last-updated").textContent = formatDate(data.generated_at);
    populateConfig(); renderSources(); render();
  } catch (error) {
    document.querySelector("#jobs").append(el("div", "empty", `Could not load tracker data: ${error.message}. Serve this folder over HTTP.`));
    document.querySelector("#source-health").textContent = "Data unavailable";
  }
}
["#search", "#company-filter", "#visa-filter", "#status-filter", "#remote-only", "#include-rejected"].forEach(selector => {
  document.querySelector(selector).addEventListener("input", render);
});
document.querySelector("#min-score").addEventListener("input", event => { document.querySelector("#min-score-value").value = event.target.value; render(); });
document.querySelector("#reset-filters").addEventListener("click", resetFilters);
document.querySelector("#export-csv").addEventListener("click", exportCsv);
start();
