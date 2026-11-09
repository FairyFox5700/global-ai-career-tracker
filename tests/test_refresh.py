import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from career_tracker.refresh import refresh


class RefreshTests(unittest.TestCase):
    def test_preserves_stale_company_jobs_when_source_fails(self):
        previous = {
            "generated_at": "2026-11-08T00:00:00Z",
            "jobs": [{
                "id": "Anthropic:old", "source_id": "old", "company": "Anthropic",
                "title": "Forward Deployed Engineer", "locations": ["London"],
                "url": "https://example.com/old", "source": "greenhouse", "source_status": "official",
                "stale": False, "compensation": None, "visa_status": "unknown",
                "visa_evidence": "No explicit visa language found in the official listing.",
            }],
        }
        specs = [
            {"company": "Anthropic", "kind": "greenhouse", "board": "anthropic"},
            {"company": "Databricks", "kind": "greenhouse", "board": "databricks"},
        ]
        live_payload = {"jobs": [{
            "id": 9, "title": "Solutions Architect", "absolute_url": "https://example.com/9",
            "location": {"name": "Germany"}, "updated_at": "2026-11-09T00:00:00Z",
            "content": "Customer architecture role",
        }]}

        def fake_fetch(spec):
            if spec["company"] == "Anthropic":
                raise RuntimeError("blocked")
            return live_payload

        with tempfile.TemporaryDirectory() as tmp:
            data_path = Path(tmp) / "jobs.json"
            report_path = Path(tmp) / "refresh-report.json"
            data_path.write_text(json.dumps(previous), encoding="utf-8")
            with patch("career_tracker.refresh._utc_now", return_value="2026-11-09T12:00:00Z"):
                result = refresh(specs, data_path, report_path, fetcher=fake_fetch)

            saved = json.loads(data_path.read_text(encoding="utf-8"))
            stale = next(job for job in saved["jobs"] if job["company"] == "Anthropic")
            self.assertTrue(stale["stale"])
            self.assertEqual("source_error", stale["source_status"])
            self.assertEqual(["Databricks"], result["sources_ok"])
            self.assertEqual(["Anthropic"], result["sources_failed"])
            self.assertEqual(2, result["job_count"])
            self.assertIn("score", saved["jobs"][0])
            self.assertEqual(result, json.loads(report_path.read_text(encoding="utf-8")))

    def test_successful_empty_source_removes_previous_company_jobs(self):
        previous = {"jobs": [{"id": "OpenAI:gone", "company": "OpenAI"}]}
        specs = [{"company": "OpenAI", "kind": "ashby", "board": "openai"}]
        with tempfile.TemporaryDirectory() as tmp:
            data_path = Path(tmp) / "jobs.json"
            report_path = Path(tmp) / "report.json"
            data_path.write_text(json.dumps(previous), encoding="utf-8")
            result = refresh(specs, data_path, report_path, fetcher=lambda spec: {"jobs": []})
            self.assertEqual(0, result["job_count"])
            self.assertEqual([], json.loads(data_path.read_text(encoding="utf-8"))["jobs"])


if __name__ == "__main__":
    unittest.main()
