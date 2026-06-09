# Local midnight publish

GS145 and QDII are generated locally by workbuddy, so GitHub Actions cannot update them directly.

The local scheduled task runs `scripts/publish_gs_qdii.ps1` after workbuddy finishes. The script publishes only:

- `pages/gs145.html`
- `pages/qdii.html`
- `reports/gs_145fund_report.html`
- `reports/qdii_fund_report.html`

It commits those files when they changed, rebases on `origin/main`, and pushes to GitHub. Netlify then deploys the new commit automatically.

Recommended schedule: `00:10` Asia/Shanghai, so it does not run at the exact same time as the Top100 GitHub Actions workflow.
