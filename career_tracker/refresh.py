import json
import os
from pathlib import Path
from datetime import datetime, timezone

from .adapters import normalize_ashby, normalize_google, normalize_greenhouse, normalize_workday
from .scoring import score_job
from .sources import fetch_source


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_previous(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")).get("jobs", [])
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def _atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _normalize(spec, payload):
    kind = spec["kind"]
    company = spec["company"]
    if kind == "greenhouse":
        return normalize_greenhouse(payload, company)
    if kind == "ashby":
        return normalize_ashby(payload, company)
    if kind == "workday":
        return normalize_workday(payload, company, spec["base_url"])
    if kind == "google":
        return normalize_google(payload, company)
    raise ValueError(f"Unsupported source kind: {kind}")


def refresh(specs, data_path, report_path, fetcher=fetch_source):
    generated_at = _utc_now()
    previous = _read_previous(data_path)
    jobs = []
    sources_ok = []
    sources_failed = []
    source_results = []

    for spec in specs:
        company = spec["company"]
        try:
            payload = fetcher(spec)
            normalized = _normalize(spec, payload)
            jobs.extend(normalized)
            sources_ok.append(company)
            source_results.append({"company": company, "status": "ok", "jobs": len(normalized)})
        except Exception as exc:  # Source isolation is intentional: one blocked site must not erase others.
            preserved = []
            for old in previous:
                if old.get("company") == company:
                    old = dict(old)
                    old["stale"] = True
                    old["source_status"] = "source_error"
                    old["stale_reason"] = str(exc)[:240]
                    preserved.append(old)
            jobs.extend(preserved)
            sources_failed.append(company)
            source_results.append({
                "company": company,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}"[:500],
                "jobs_preserved": len(preserved),
            })

    deduplicated = {job["id"]: job for job in jobs if job.get("id")}
    jobs = list(deduplicated.values())
    for job in jobs:
        scoring_input = dict(job)
        scoring_input["description"] = job.get("description_excerpt", "")
        job["score"] = score_job(scoring_input, now=generated_at)
    jobs.sort(key=lambda job: (-job["score"]["total"], job.get("company", ""), job.get("title", "")))

    data = {"generated_at": generated_at, "count": len(jobs), "jobs": jobs}
    report = {
        "generated_at": generated_at,
        "job_count": len(jobs),
        "sources_ok": sources_ok,
        "sources_failed": sources_failed,
        "sources": source_results,
    }
    _atomic_json(data_path, data)
    _atomic_json(report_path, report)
    return report
