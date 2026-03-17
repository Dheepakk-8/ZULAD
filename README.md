# Zenoti University Learning Analytics Dashboard

Phase 1 implementation of an API-driven learning analytics dashboard for Northpass LMS.

## Features
- Backend-only Northpass API integration using `X-Api-Key` authentication.
- Full pagination traversal (`next` URL and Link header support).
- Filterable dashboard with date/course/group/learner/completion band.
- KPI cards for enrollments, completion, in-progress, drop-offs.
- Course analytics table and rule-based AI insight panel.
- Export filtered data to CSV or Excel.

## Quick Start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export NORTHPASS_API_KEY="your_api_key"
python -m dashboard.app
```

Open http://localhost:8000.

## API Endpoints
- `GET /api/filters` - Filter options.
- `GET /api/dashboard` - KPI + course analytics.
- `GET /api/export?format=csv|xlsx` - Data export.

## Notes
- API keys are loaded from environment variables and never exposed to frontend code.
- Dataset snapshots are cached in-memory for 5 minutes (configurable with `CACHE_SECONDS`).
- Initial lesson-level analytics and per-lesson drop-off are scaffolded for future expansion when activity completion telemetry is available.
