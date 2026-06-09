# Local midnight publish

GS145, QDII, and Top100 data are generated locally by workbuddy, so GitHub Actions cannot update them directly.

The local scheduled task runs `scripts/publish_gs_qdii.ps1` after workbuddy finishes. The script publishes only the report shells/templates and their data JSON:

- `pages/gs145.html`
- `pages/qdii.html`
- `pages/top100.html`
- `reports/gs_145fund_report.html`
- `reports/qdii_fund_report.html`
- `reports/top_100.html`
- `reports/gs145_data.json`
- `reports/qdii_data.json`
- `reports/top100_data.json`

It commits those files when they changed, rebases on `origin/main`, and pushes to GitHub. Netlify then deploys the new commit automatically.

Recommended schedule: `00:10` Asia/Shanghai, after workbuddy's `23:00` data generation has finished.
