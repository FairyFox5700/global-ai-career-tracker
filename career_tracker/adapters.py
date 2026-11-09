import html
import re
from urllib.parse import urljoin

TARGET_ROLE_PATTERNS = tuple(re.compile(pattern, re.I) for pattern in (
    r"\bforward deployed\b", r"\bfde\b",
    r"\bapplied ai (?:engineer|architect)\b",
    r"\bapplied ai solution (?:engineer|architect|consultant)\b",
    r"\bai platform engineer\b", r"\bai deployment engineer\b",
    r"\b(?:ai |cloud )?customer engineer\b",
    r"\bdelivery (?:solutions? )?architect\b",
    r"\bsolutions? architect\b", r"\bfield engineer\b",
    r"\bsolutions? engineer\b", r"\bdeployment engineer\b",
    r"\bdeployment lead\b", r"\btechnical consultant\b",
    r"\bcustomer success architect\b", r"\btechnical account architect\b",
))

EXCLUDED_ROLE_PATTERNS = tuple(re.compile(pattern, re.I) for pattern in (
    r"\brecruit(?:er|ing)\b", r"\baccounting\b", r"\bintern(?:ship)?\b",
    r"\bgraduate\b", r"\bmanager\b", r"\bdirector\b", r"\bhead of\b",
    r"\bprogram manager\b", r"\bengagement manager\b", r"\benablement\b",
    r"\bstrategist\b",
))


def _text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _target(title):
    text = title or ""
    return (
        not any(pattern.search(text) for pattern in EXCLUDED_ROLE_PATTERNS)
        and any(pattern.search(text) for pattern in TARGET_ROLE_PATTERNS)
    )


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
        r"(?P<prefix>US\$|C\$|A\$|\$|£|€|EUR|USD|GBP|CAD|AUD|CHF|SGD|AED)\s*"
        r"(?P<low>[\d,.]+)\s*(?:-|–|—|to)\s*"
        r"(?:(?:US\$|C\$|A\$|\$|£|€|EUR|USD|GBP|CAD|AUD|CHF|SGD|AED)\s*)?"
        r"(?P<high>[\d,.]+)\s*(?P<suffix>EUR|USD|GBP|CAD|AUD|CHF|SGD|AED)?"
        r"(?:\s*per\s*year|\s*annually)?",
        clean,
        re.I,
    )
    if not match:
        return None
    prefix = match.group("prefix").upper()
    suffix = (match.group("suffix") or "").upper()
    symbol_currency = {
        "€": "EUR", "£": "GBP", "$": "USD", "US$": "USD",
        "C$": "CAD", "A$": "AUD",
    }
    currency = suffix or symbol_currency.get(prefix, prefix)
    low = float(match.group("low").replace(",", ""))
    high = float(match.group("high").replace(",", ""))
    return {"currency": currency, "min": int(low), "max": int(high), "period": "year", "verified": True}


def _excerpt(text, limit=420):
    return _text(text)[:limit]


def _base(company, source, source_id, title, locations, url, posted_at, description):
    visa_status, visa_evidence = _evidence(description)
    locations = [location for location in locations if location]
    return {
        "id": f"{company}:{source_id}",
        "source_id": str(source_id),
        "company": company,
        "title": title,
        "locations": locations,
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
