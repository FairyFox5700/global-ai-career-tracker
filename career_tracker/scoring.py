from datetime import datetime, timezone

TARGET_COMPENSATION_EUR = 120_000


def _parse_date(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def score_job(job, now=None):
    """Return deterministic weighted fit score and rejection metadata."""
    title = (job.get("title") or "").lower()
    text = f"{title} {(job.get('description') or '').lower()}"

    role_terms = {
        "engineering": ("engineer", "hands-on", "deployment"),
        "architecture": ("architect", "architecture", "solutions"),
        "customers": ("customer", "field", "forward deployed", "consultant"),
    }
    role_hits = sum(any(term in text for term in terms) for terms in role_terms.values())
    role_score = {0: 0, 1: 12, 2: 22, 3: 30}[role_hits]

    travel = job.get("travel_percent")
    if isinstance(travel, (int, float)):
        travel_score = 20 if 25 <= travel <= 40 else (10 if 10 <= travel <= 60 else 2)
    else:
        travel_score = 6

    compensation = job.get("compensation")
    hard_reject = False
    if not compensation or compensation.get("max") is None:
        compensation_score = 6
        compensation_status = "needs_validation"
    elif compensation.get("currency") == "EUR" and compensation.get("period") == "year":
        ceiling = compensation["max"]
        if compensation.get("verified") and ceiling < TARGET_COMPENSATION_EUR:
            hard_reject = True
            compensation_score = 0
            compensation_status = "below_target"
        elif ceiling >= TARGET_COMPENSATION_EUR:
            compensation_score = 20
            compensation_status = "meets_target"
        else:
            compensation_score = 4
            compensation_status = "needs_validation"
    else:
        compensation_score = 6
        compensation_status = "needs_validation"

    visa = job.get("visa_status", "unknown")
    visa_score = {"sponsored": 15, "supported": 12, "not_supported": 0, "unknown": 5}.get(visa, 5)

    seniority_text = f"{title} {(job.get('seniority') or '').lower()}"
    if any(term in seniority_text for term in ("principal", "staff", "lead", "senior")):
        seniority_score = 10
    elif any(term in seniority_text for term in ("engineer", "architect", "consultant")):
        seniority_score = 7
    else:
        seniority_score = 3

    freshness_score = 0
    if job.get("source_status") == "official":
        freshness_score += 2
    posted_at = _parse_date(job.get("posted_at"))
    current = _parse_date(now) if isinstance(now, str) else (now or datetime.now(timezone.utc))
    if posted_at:
        age = max(0, (current - posted_at).days)
        freshness_score += 3 if age <= 7 else (2 if age <= 30 else (1 if age <= 90 else 0))

    breakdown = {
        "role_blend": role_score,
        "travel": travel_score,
        "compensation": compensation_score,
        "visa": visa_score,
        "skill_seniority": seniority_score,
        "freshness_source": freshness_score,
    }
    return {
        "total": sum(breakdown.values()),
        "breakdown": breakdown,
        "hard_reject": hard_reject,
        "compensation_status": compensation_status,
    }
