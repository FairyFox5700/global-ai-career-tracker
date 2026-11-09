import json
import unittest
from unittest.mock import patch

from career_tracker.sources import fetch_source


class FakeResponse:
    def __init__(self, payload, content_type="application/json"):
        self.body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class SourceTests(unittest.TestCase):
    def test_greenhouse_uses_public_board_api_with_content(self):
        calls = []

        def opener(request, timeout):
            calls.append((request, timeout))
            return FakeResponse({"jobs": []})

        payload = fetch_source({"kind": "greenhouse", "board": "anthropic", "company": "Anthropic"}, opener=opener)
        self.assertEqual({"jobs": []}, payload)
        self.assertEqual("https://boards-api.greenhouse.io/v1/boards/anthropic/jobs?content=true", calls[0][0].full_url)
        self.assertIn("GlobalAITracker", calls[0][0].get_header("User-agent"))

    def test_workday_posts_expected_public_search_payload(self):
        calls = []

        def opener(request, timeout):
            calls.append(request)
            return FakeResponse({"total": 1, "jobPostings": [{"title": "Solutions Architect"}]})

        spec = {
            "kind": "workday", "company": "NVIDIA", "host": "nvidia.wd5.myworkdayjobs.com",
            "tenant": "nvidia", "site": "NVIDIAExternalCareerSite",
            "base_url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
        }
        result = fetch_source(spec, opener=opener)
        self.assertEqual(1, len(result["jobPostings"]))
        request = calls[0]
        self.assertEqual("POST", request.method)
        self.assertEqual(
            "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs",
            request.full_url,
        )
        sent = json.loads(request.data)
        self.assertEqual(20, sent["limit"])
        self.assertEqual(0, sent["offset"])

    def test_google_extracts_official_jobposting_json_ld(self):
        html = b'''<script type="application/ld+json">{"@type":"JobPosting","identifier":{"value":"G123"},"title":"Customer Engineer, AI","description":"Cloud customer architecture","datePosted":"2026-11-08","jobLocation":{"address":{"addressLocality":"Berlin","addressCountry":"DE"}},"url":"https://www.google.com/about/careers/applications/jobs/results/123"}</script>'''
        with patch("career_tracker.sources._google_result_urls", return_value=["https://www.google.com/job"]):
            result = fetch_source(
                {"kind": "google", "company": "Google Cloud", "search_url": "https://www.google.com/careers"},
                opener=lambda request, timeout: FakeResponse(html, "text/html"),
            )
        self.assertEqual("G123", result["jobs"][0]["id"])
        self.assertEqual(["Berlin, DE"], result["jobs"][0]["locations"])


if __name__ == "__main__":
    unittest.main()
