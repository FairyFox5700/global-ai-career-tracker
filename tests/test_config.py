import json
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]


class ConfigTests(unittest.TestCase):
    def test_tracker_configuration_has_requested_sources_and_weights(self):
        config = json.loads((ROOT / "config" / "tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(
            ["Databricks", "OpenAI", "Anthropic", "Celonis", "Google Cloud", "Salesforce", "NVIDIA", "Aircall"],
            [source["company"] for source in config["sources"]],
        )
        self.assertEqual(
            {"role_blend": 30, "travel": 20, "compensation": 20, "visa": 15, "skill_seniority": 10, "freshness_source": 5},
            config["ranking_weights"],
        )
        self.assertEqual(120000, config["preferences"]["minimum_total_compensation_eur"])
        self.assertEqual([25, 40], config["preferences"]["preferred_travel_percent"])
        self.assertIn("Germany", config["preferences"]["visa_friendly_countries"])

    def test_no_source_requires_secrets(self):
        config = json.loads((ROOT / "config" / "tracker.json").read_text(encoding="utf-8"))
        serialized = json.dumps(config).lower()
        self.assertNotIn("token", serialized)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("api_key", serialized)


if __name__ == "__main__":
    unittest.main()
