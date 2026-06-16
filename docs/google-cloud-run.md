# Google Cloud Run Deployment

This project is configured for Google Cloud Run deployment.

## Prerequisites

- Google Cloud CLI installed and authenticated with `gcloud auth login`.
- A Google Cloud project with billing enabled.
- The FastAPI app listens on the `PORT` environment variable, defaulting to `8080`.
- No secrets committed to the repository.

## One-Time Setup

```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
```

Optional Gemini secret:

```powershell
echo "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
```

Grant the Cloud Run runtime service account access to the secret if the app will read it at runtime.

Optional Firestore persistence:

```powershell
gcloud services enable firestore.googleapis.com
```

Set `FIRESTORE_ENABLED=true` in Cloud Run after Firestore is configured.

## Deploy From Source

```powershell
$env:GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
$env:GOOGLE_CLOUD_REGION="us-central1"
$env:CLOUD_RUN_SERVICE="promptwars-agent"

.\scripts\deploy-cloud-run.ps1 -AllowUnauthenticated
```

Omit `-AllowUnauthenticated` for a private service.

For Gemini in production, configure the Cloud Run service with a Secret Manager-backed `GEMINI_API_KEY`.



## Cloud Run Contract

Cloud Run expects the container to:

- Listen on `0.0.0.0:$PORT`.
- Start quickly and return non-zero on startup failure.
- Keep API keys in environment variables or Secret Manager, not source files.
- Write logs to stdout/stderr.

## Suggested App Layout

```text
frontend/
backend/
  agent.py
  tools.py
  prompts.py
tests/
docs/
```

When the backend exists, add a runtime-specific `Dockerfile` only if source deploy cannot infer the build correctly.
