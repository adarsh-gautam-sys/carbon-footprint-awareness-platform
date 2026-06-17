# 🌱 Carbon Footprint Awareness Platform

**PromptWars 2026 — Challenge 3**

> *Design a solution that helps individuals understand, track, and reduce their carbon footprint through simple actions and personalised insights.*

**Live on Google Cloud Run:** https://promptwars-agent-239331599550.us-central1.run.app

---

## What This Does

The Carbon Footprint Awareness Platform is a production-ready web application that:

1. **Understands** your lifestyle (home energy, transport, food, and purchasing habits)
2. **Calculates** a transparent monthly CO₂e estimate using published IPCC/EPA/DEFRA emission factors
3. **Ranks** personalised reduction actions by estimated monthly impact
4. **Explains** your results using Gemini AI in non-judgmental, practical language
5. **Compares** your footprint to global benchmarks (India average, world average, Paris 1.5°C target)

---

## Features

| Layer | What it does |
|---|---|
| **API Service** | FastAPI backend with Pydantic validation, typed OpenAPI schema, and configurable CORS |
| **AI Engine** | Gemini 2.0 Flash for personalised insights; deterministic fallback always works |
| **Carbon Engine** | Transparent factor-based calculations with source citations in code |
| **Storage** | Firestore (production) or local JSONL (development) |
| **Deployment** | Dockerfile + Cloud Run PowerShell script + service YAML |
| **Tests** | 42 passed tests: unit, integration, edge cases, validation, and API boundary tests |

---

## Local Development

```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Optional: configure Gemini
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Run development server
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000** — the API and service work without a Gemini key using deterministic fallback insights.

---

## Tests

```powershell
pytest tests\ -v
```

Expected: **41 passed** across three test files.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | _(empty)_ | Gemini API key — app falls back gracefully if missing |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Override the Gemini model |
| `GOOGLE_CLOUD_PROJECT` | _(required for deploy)_ | GCP project ID |
| `GOOGLE_CLOUD_REGION` | `us-central1` | Cloud Run region |
| `FIRESTORE_ENABLED` | `false` | Set `true` to persist assessments in Firestore |
| `LOCAL_DATA_DIR` | system temp | Local JSONL storage path for development |
| `ALLOWED_ORIGINS` | `*` | Comma-separated allowed CORS origins for production |

Copy `.env.example` to `.env` for local development. **Never commit real secrets.**

---

## Cloud Run Deployment

```powershell
$env:GOOGLE_CLOUD_PROJECT = "your-project-id"
$env:GOOGLE_CLOUD_REGION  = "us-central1"
.\scripts\deploy-cloud-run.ps1 -AllowUnauthenticated
```

See [`docs/google-cloud-run.md`](docs/google-cloud-run.md) for full setup including Secret Manager for the Gemini key and optional Firestore persistence.

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System design, data flow, Mermaid diagram, agent decision logic |
| [`docs/tool-usage.md`](docs/tool-usage.md) | All Google tools used and why each was selected |
| [`docs/prompt-engineering.md`](docs/prompt-engineering.md) | Prompt iterations from initial to final optimised version |
| [`docs/human-ai-responsibilities.md`](docs/human-ai-responsibilities.md) | Clear separation of human vs AI roles |
| [`docs/scoring-checklist.md`](docs/scoring-checklist.md) | PromptWars judging criteria self-assessment |
| [`docs/security-check.md`](docs/security-check.md) | Security audit report, threat model, and dependency analysis |
| [`docs/google-cloud-run.md`](docs/google-cloud-run.md) | Deployment prerequisites and step-by-step guide |
| [`docs/linkedin-post-draft.md`](docs/linkedin-post-draft.md) | Draft social post for submission validation |

---

## Architecture Overview

```
Client / API Client
    │  POST /api/footprint
    ▼
FastAPI + Pydantic validation
    │
    ├─► Carbon engine (carbon.py)
    │       IPCC/EPA emission factors
    │       Home + Transport + Lifestyle
    │
    ├─► Action ranker
    │       Ranked by kg CO2e saved/month
    │
    ├─► Gemini 2.0 Flash (insights.py)
    │       System instruction + grounded prompt
    │       Deterministic fallback if unavailable
    │
    └─► Storage (storage.py)
            Firestore (production)
            Local JSONL (development)
```

---

## Emission Factors (Key References)

- Transport: DEFRA 2023 GHG Conversion Factors
- Electricity: India CEA Grid Emission Factor 2022-23 (0.71 kg CO₂e/kWh)
- Diet: Poore & Nemecek (2018), Oxford University food systems research
- Gas: EPA AP-42 combustion factors
- Goods and waste: EPA WARM model lifecycle averages

---

## Why AI Is Necessary

Raw carbon numbers alone do not change behaviour. The platform uses Gemini to:

1. **Interpret** ambiguous lifestyle inputs in context of the user's goal
2. **Prioritise** the highest-impact action in language matched to the user's motivation
3. **Phrase** recommendations without guilt, in the user's own goal framing (save money vs. reduce emissions)
4. **Personalise** each insight using real calculated data — no hallucinated claims

The deterministic engine ensures correctness; Gemini ensures engagement and personalisation.
