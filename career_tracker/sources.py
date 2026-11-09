import html as html_module
import json
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen

USER_AGENT = "GlobalAITracker/1.0 (+static career research; official sources only)"


def _request_json(url, opener, data=None):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json,text/html;q=0.9"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with opener(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _google_result_urls(search_url, opener):
    request = Request(search_url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with opener(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
    links = re.findall(r'href=["\']([^"\']*/about/careers/applications/jobs/results/[^"\'#?]+)', body, re.I)
    normalized = []
    for link in links:
        url = urljoin("https://www.google.com", html_module.unescape(link))
        if url not in normalized:
            normalized.append(url)
    if not normalized:
        raise RuntimeError("Google Careers returned no official job result links")
    return normalized


def _json_ld_objects(raw):
    if isinstance(raw, list):
        for item in raw:
            yield from _json_ld_objects(item)
    elif isinstance(raw, dict):
        if raw.get("@type") == "JobPosting" or "JobPosting" in (raw.get("@type") or []):
            yield raw
        for item in raw.get("@graph", []):
            yield from _json_ld_objects(item)


def _google_job(url, opener):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with opener(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
    for raw in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', body, re.I | re.S):
        try:
            parsed = json.loads(html_module.unescape(raw))
        except json.JSONDecodeError:
            continue
        for item in _json_ld_objects(parsed):
            identifier = item.get("identifier")
            source_id = identifier.get("value") if isinstance(identifier, dict) else identifier
            location_values = item.get("jobLocation") or []
            if isinstance(location_values, dict):
                location_values = [location_values]
            locations = []
            for location in location_values:
                address = location.get("address", {}) if isinstance(location, dict) else {}
                if isinstance(address, str):
                    locations.append(address)
                else:
                    locality = address.get("addressLocality")
                    country = address.get("addressCountry")
                    if isinstance(country, dict):
                        country = country.get("name")
                    locations.append(", ".join(part for part in (locality, country) if part))
            return {
                "id": str(source_id or item.get("url") or url),
                "title": item.get("title"),
                "locations": locations,
                "apply_url": item.get("url") or url,
                "description": item.get("description") or "",
                "date_published": item.get("datePosted"),
            }
    return None


def fetch_source(spec, opener=None):
    opener = opener or urlopen
    kind = spec["kind"]
    if kind == "greenhouse":
        url = f"https://boards-api.greenhouse.io/v1/boards/{spec['board']}/jobs?content=true"
        return _request_json(url, opener)
    if kind == "ashby":
        url = f"https://api.ashbyhq.com/posting-api/job-board/{spec['board']}"
        return _request_json(url, opener)
    if kind == "workday":
        url = f"https://{spec['host']}/wday/cxs/{spec['tenant']}/{spec['site']}/jobs"
        postings = []
        offset = 0
        while True:
            data = json.dumps({"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": ""}).encode("utf-8")
            page = _request_json(url, opener, data=data)
            batch = page.get("jobPostings", [])
            postings.extend(batch)
            offset += len(batch)
            total = int(page.get("total", len(postings)))
            if not batch or offset >= total:
                break
        return {"jobPostings": postings}
    if kind == "google":
        urls = _google_result_urls(spec["search_url"], opener)
        jobs = []
        for url in urls:
            job = _google_job(url, opener)
            if job:
                jobs.append(job)
        if not jobs:
            raise RuntimeError("Google Careers result pages contained no parseable JobPosting data")
        return {"jobs": jobs}
    raise ValueError(f"Unsupported source kind: {kind}")
