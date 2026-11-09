# Global AI Career Tracker

A static, local-first opportunity dashboard for Iryna. It ranks current roles from official company sources against a €120k minimum total-compensation target, preferred 25–40% travel, visa evidence, and a work mix spanning hands-on engineering, architecture, and customers.

No third-party packages, API keys, analytics, or backend are required. Pipeline statuses remain in browser `localStorage`.

## Local use

Python 3.11+ is sufficient.

```bash
python scripts/refresh.py
python -m http.server 8765
```

Open <http://localhost:8765>. Do not open `index.html` directly from `file://`; browsers block its JSON fetches.

Run all checks:

```bash
python -m unittest discover -s tests -v
python -m compileall -q career_tracker scripts
```

## Data and ranking

`config/tracker.json` is the source of truth for companies, preferences, target roles, weights, and recruiter travel questions. The refresh writes normalized, deduplicated records to `data/jobs.json` and source-level diagnostics to `data/refresh-report.json`.

Only target-role results are retained. The generated JSON stores short official excerpts, visa evidence excerpts, and official links—not full job descriptions.

The 100-point score is:

| Signal | Weight |
|---|---:|
| Role blend | 30 |
| Travel fit | 20 |
| Compensation | 20 |
| Visa support | 15 |
| Skill/seniority | 10 |
| Freshness and official source | 5 |

A role is hard-rejected only when an official, normalized annual EUR compensation ceiling is verified below €120,000. Missing or non-comparable compensation remains `needs_validation`.

## Official sources

- Greenhouse public board API: Databricks, Anthropic, Celonis, Aircall
- Ashby public job board feed: OpenAI
- Workday public career endpoints: Salesforce, NVIDIA
- Official Google Careers result pages: Google Cloud

The adapters use only public endpoints and require no secrets.

## Source failures

Each source is isolated. A blocked or changed endpoint is recorded in the refresh report, while the other sources continue. Existing roles for a failed source are preserved and marked stale/source error rather than silently deleted. A successful empty source removes that company's old records.

## Dashboard behavior

- Search and filter by company, visa signal, score, remote status, and personal pipeline status.
- Inspect every score component and the short official evidence excerpt.
- Keep statuses locally as New, Reviewing, Applied, Interviewing, Offer, or Archived.
- Export the filtered view to CSV with both a raw URL and an Excel/Sheets-style `HYPERLINK` column.
- Review source health and recruiter travel questions in the dashboard.

## Automation

- `ci.yml` runs tests and Python compilation.
- `refresh.yml` refreshes daily and commits only generated JSON changes.
- `pages.yml` explicitly deploys the static repository to GitHub Pages.

The workflow files use GitHub's built-in permissions only; no repository secrets are referenced.

## License

MIT. See [LICENSE](LICENSE).
