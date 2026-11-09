import html
import re
from urllib.parse import urljoin

TARGET_ROLE_PHRASES = (
    "forward deployed", "fde", "applied ai", "ai engineer", "ai architect",
    "customer engineer", "delivery architect", "solutions architect", "solution architect",
    "field engineer", "solutions engineer", "solution engineer", "deployment engineer",
    "technical consultant", "customer success architect", "technical account",
)


def _text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _target(title):
    lower = (title or "").lower()
    return any(phrase in lower for phrase in TARGET_ROLE_PHRASES)


def _evidence(text):
    clean = _text(text)
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    negative = ("cannot provide", "unable to provide", "no visa sponsorship", "not sponsor", "does not sponsor")
    positive = ("visa sponsorship", "sponsorship is available", "sponsor visas")
    supported = ("immigration support", "relocation and immigration", "visa support")
    for sentence in sentences:
        low = sentence.lower()
        if any(term in low for term in negative):
            return "not_supported", sentence[:220]
    for sentence in sentences:
        low = sentence.lower()
        if any(term in low for term in positive):
            return "sponsored", sentence[:220]
    for sentence in sentences:
        low = sentence.lower()
        if any(term in low for term in supported):
            return "supported", sentence[:220]
    return "unknown", "No explicit visa language found in the official listing."


def _travel(text):
    patterns = (
        r"(?:travel(?:\s+(?:up\s+to|required))?|up\s+to)\D{0,16}(\d{1,2})\s*%",
        r"(\d{1,2})\s*%\s+travel",
    )
    for pattern in patterns:
        match = re.search(pattern, _text(text), re.I)
        if match:
            return int(match.group(1))
    return None


def _compensation(text):
    clean = _text(text)
    match = re.search(
        r"(?:EUR|€)\s*([\d,.]+)\s*(?:-|–|to)\s*(?:EUR|€)?\s*([\d,.]+)(?:\s*per\s*year|\s*annually)?",
        clean,
        re.I,
    )
    if not match:
        return None
    low = float(match.group(1).replace(",", ""))
    high = float(match.group(2).replace(",", ""))
    return {"currency": "EUR", "min": int(low), "max": int(high), "period": "year", "verified": True}


def _excerpt(text, limit=420):
    return _text(text)[:limit]


def _base(company, source, source_id, title, locations, url, posted_at, description):
    visa_status, visa_evidence = _evidence(description)
    return {
        "id": f"{company}:{source_id}",
        "source_id": str(source_id),
        "company": company,
        "title": title,
        "locations": [location for location in locations if location],
        "remote": "remote" in " ".join(locations).lower(),
        "url": url,
        "posted_at": posted_at,
        "description_excerpt": _excerpt(description),
        "travel_percent": _travel(description),
        "compensation": _compensation(description),
        "visa_status": visa_status,
        "visa_evidence": visa_evidence,
        "source": source,
        "source_status": "official",
        "stale": False,
    }


def normalize_greenhouse(payload, company):
    result = []
    for raw in payload.get("jobs", []):
        if not _target(raw.get("title")):
            continue
        result.append(_base(
            company, "greenhouse", raw.get("id"), raw.get("title"),
            [(raw.get("location") or {}).get("name")], raw.get("absolute_url"),
            raw.get("updated_at"), raw.get("content", ""),
        ))
    return result


def normalize_ashby(payload, company):
    result = []
    for raw in payload.get("jobs", []):
        if not _target(raw.get("title")):
            continue
        location = raw.get("location") or ""
        job = _base(
            company, "ashby", raw.get("id"), raw.get("title"), [location],
            raw.get("jobUrl") or raw.get("applyUrl"), raw.get("publishedAt"),
            raw.get("descriptionPlain") or raw.get("descriptionHtml") or "",
        )
        job["remote"] = bool(raw.get("isRemote")) or job["remote"]
        result.append(job)
    return result


def normalize_workday(payload, company, base_url):
    result = []
    for raw in payload.get("jobPostings", []):
        if not _target(raw.get("title")):
            continue
        source_id = raw.get("jobReqId") or raw.get("externalPath")
        locations = [raw.get("locationsText")] if raw.get("locationsText") else list(raw.get("bulletFields") or [])[:1]
        description = raw.get("jobDescription") or ""
        result.append(_base(
            company, "workday", source_id, raw.get("title"), locations,
            urljoin(base_url.rstrip("/") + "/", (raw.get("externalPath") or "").lstrip("/")),
            raw.get("postedAt") or None, description,
        ))
    return result


def normalize_google(payload, company):
    result = []
    for raw in payload.get("jobs", []):
        if not _target(raw.get("title")):
            continue
        result.append(_base(
            company, "google_careers", raw.get("id"), raw.get("title"),
            raw.get("locations") or [], raw.get("apply_url") or raw.get("url"),
            raw.get("date_published"), raw.get("description") or "",
        ))
    return result
