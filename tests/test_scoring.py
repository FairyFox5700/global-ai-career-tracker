import unittest
from career_tracker.scoring import score_job


class ScoringTests(unittest.TestCase):
    def test_exact_weighted_score_and_breakdown(self):
        job = {
            "title": "Forward Deployed Engineer",
            "description": "Hands-on customer architecture and deployment",
            "travel_percent": 30,
            "compensation": {"currency": "EUR", "max": 150000, "period": "year"},
            "visa_status": "sponsored",
            "seniority": "principal",
            "posted_at": "2026-11-08T12:00:00Z",
            "source_status": "official",
        }
        result = score_job(job, now="2026-11-09T12:00:00Z")
        self.assertEqual(100, result["total"])
        self.assertEqual(
            {"role_blend": 30, "travel": 20, "compensation": 20, "visa": 15, "skill_seniority": 10, "freshness_source": 5},
            result["breakdown"],
        )
        self.assertFalse(result["hard_reject"])

    def test_unknown_compensation_needs_validation_not_rejection(self):
        result = score_job({"title": "Applied AI Engineer", "compensation": None}, now="2026-11-09T12:00:00Z")
        self.assertFalse(result["hard_reject"])
        self.assertEqual("needs_validation", result["compensation_status"])

    def test_verified_ceiling_below_target_is_hard_rejected(self):
        job = {
            "title": "Solutions Architect",
            "compensation": {"currency": "EUR", "max": 110000, "period": "year", "verified": True},
        }
        result = score_job(job, now="2026-11-09T12:00:00Z")
        self.assertTrue(result["hard_reject"])
        self.assertEqual("below_target", result["compensation_status"])


if __name__ == "__main__":
    unittest.main()
