from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]


class SiteContractTests(unittest.TestCase):
    def test_dashboard_has_required_controls_and_accessible_regions(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        for required_id in (
            'id="search"', 'id="company-filter"', 'id="visa-filter"',
            'id="status-filter"', 'id="min-score"', 'id="export-csv"',
            'id="jobs"', 'id="source-health"', 'id="travel-help"',
        ):
            self.assertIn(required_id, page)
        self.assertIn('aria-live="polite"', page)
        self.assertNotIn("fonts.googleapis.com", page)
        self.assertNotIn("cdn.", page)

    def test_javascript_uses_browser_local_statuses_and_score_breakdown(self):
        script = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")
        self.assertIn("localStorage", script)
        self.assertIn("global-ai-career-tracker-statuses-v1", script)
        self.assertIn("score.breakdown", script)
        self.assertIn("description_excerpt", script)
        self.assertIn("visa_evidence", script)

    def test_csv_has_raw_and_spreadsheet_clickable_links(self):
        script = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")
        self.assertIn('"raw_url"', script)
        self.assertIn('"spreadsheet_link"', script)
        self.assertIn('HYPERLINK(', script)

    def test_styles_include_mobile_and_reduced_motion_support(self):
        styles = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 700px)", styles)
        self.assertIn("prefers-reduced-motion", styles)
        self.assertIn("min-height: 44px", styles)


if __name__ == "__main__":
    unittest.main()
