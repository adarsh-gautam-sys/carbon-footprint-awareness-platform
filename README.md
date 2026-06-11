# Carbon Footprint Awareness Platform

PromptWars 2026 Challenge 3 solution that helps individuals understand, track, and reduce their carbon footprint through simple actions and personalized insights.

## Features

- Carbon footprint estimate across home energy, transport, food, and lifestyle.
- Personalized action recommendations ranked by estimated monthly impact.
- Gemini-powered insights when `GEMINI_API_KEY` is configured.
- Deterministic fallback insights for reliable demos.
- Optional Firestore persistence.
- Cloud Run-ready Dockerfile and deployment script.
- Sequential Thinking MCP configured in `mcp.json`.

## Local Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Tests

```powershell
pytest
```

## Documentation

- Architecture: `docs/architecture.md`
- Tool usage: `docs/tool-usage.md`
- Prompt engineering: `docs/prompt-engineering.md`
- Scoring checklist: `docs/scoring-checklist.md`
- Cloud Run setup: `docs/google-cloud-run.md`

## Deploy

After adding application code that listens on `$PORT`:

```powershell
$env:GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
.\scripts\deploy-cloud-run.ps1 -AllowUnauthenticated
```
