import json
from pathlib import Path
import unittest

from career_tracker.adapters import normalize_ashby, normalize_google, normalize_greenhouse, normalize_workday

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class AdapterTests(unittest.TestCase):
    def test_greenhouse_normalizes_only_target_roles_with_evidence(self):
        jobs = normalize_greenhouse(fixture("greenhouse_jobs.json"), "Databricks")
        self.assertEqual(1, len(jobs))
        job = jobs[0]
        self.assertEqual("Databricks:101", job["id"])
        self.assertEqual(["Berlin, Germany"], job["locations"])
        self.assertEqual(30, job["travel_percent"])
        self.assertEqual("sponsored", job["visa_status"])
        self.assertLessEqual(len(job["visa_evidence"]), 220)
        self.assertEqual(160000, job["compensation"]["max"])
        self.assertNotIn("description", job)

    def test_ashby_detects_explicit_no_sponsorship(self):
        job = normalize_ashby(fixture("ashby_jobs.json"), "OpenAI")[0]
        self.assertEqual("OpenAI:ash-1", job["id"])
        self.assertEqual("not_supported", job["visa_status"])
        self.assertIn("cannot provide", job["visa_evidence"].lower())

    def test_workday_builds_official_url_and_unknown_evidence(self):
        jobs = normalize_workday(
            fixture("workday_jobs.json"), "Salesforce", "https://salesforce.wd12.myworkdayjobs.com/External_Career_Site"
        )
        self.assertEqual(1, len(jobs))
        self.assertTrue(jobs[0]["url"].startswith("https://salesforce.wd12.myworkdayjobs.com"))
        self.assertEqual("unknown", jobs[0]["visa_status"])

    def test_google_normalizes_official_results(self):
        job = normalize_google(fixture("google_jobs.json"), "Google Cloud")[0]
        self.assertEqual("supported", job["visa_status"])
        self.assertEqual(25, job["travel_percent"])
        self.assertEqual("g-1", job["source_id"])

    def test_title_filter_excludes_non_delivery_false_positives(self):
        payload = {"jobs": [
            {"id": 1, "title": "Recruiter, Applied AI", "absolute_url": "https://example.com/1", "location": {"name": "Berlin"}},
            {"id": 2, "title": "Director, Technical Accounting", "absolute_url": "https://example.com/2", "location": {"name": "Berlin"}},
            {"id": 3, "title": "Senior Perception AI Engineer", "absolute_url": "https://example.com/3", "location": {"name": "Berlin"}},
            {"id": 4, "title": "Manager, Forward Deployed Engineering", "absolute_url": "https://example.com/4", "location": {"name": "Berlin"}},
            {"id": 5, "title": "Intern Applied AI Solution Consulting", "absolute_url": "https://example.com/5", "location": {"name": "Berlin"}},
            {"id": 6, "title": "Staff Forward Deployed Engineer", "absolute_url": "https://example.com/6", "location": {"name": "Berlin"}},
            {"id": 7, "title": "Applied AI Architect", "absolute_url": "https://example.com/7", "location": {"name": "Berlin"}},
            {"id": 8, "title": "AI Platform Engineer, Customer Delivery", "absolute_url": "https://example.com/8", "location": {"name": "Berlin"}},
        ]}
        jobs = normalize_greenhouse(payload, "Example")
        self.assertEqual(
            ["Staff Forward Deployed Engineer", "Applied AI Architect", "AI Platform Engineer, Customer Delivery"],
            [job["title"] for job in jobs],
        )

    def test_compensation_parses_verified_usd_and_gbp_ranges(self):
        payload = {"jobs": [
            {"id": 1, "title": "Forward Deployed Engineer", "absolute_url": "https://example.com/1",
             "location": {"name": "New York"},
             "content": "Annual Salary: $280,000 — $320,000 USD"},
            {"id": 2, "title": "Solutions Architect", "absolute_url": "https://example.com/2",
             "location": {"name": "London"},
             "content": "Base salary £120,000 - £160,000 per year"},
        ]}
        jobs = normalize_greenhouse(payload, "Example")
        self.assertEqual(
            [
                {"currency": "USD", "min": 280000, "max": 320000, "period": "year", "verified": True},
                {"currency": "GBP", "min": 120000, "max": 160000, "period": "year", "verified": True},
            ],
            [job["compensation"] for job in jobs],
        )


if __name__ == "__main__":
    unittest.main()
