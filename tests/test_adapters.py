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


if __name__ == "__main__":
    unittest.main()
