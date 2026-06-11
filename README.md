# PromptWars 2

Deployment and MCP scaffolding for a PromptWars AI agent project.

## Current Setup

- Sequential Thinking MCP server configured in `mcp.json`.
- Google Cloud Run deployment helper in `scripts/deploy-cloud-run.ps1`.
- Cloud Run service template in `deploy/cloud-run-service.yaml`.
- Setup notes in `docs/google-cloud-run.md`.

## Deploy

After adding application code that listens on `$PORT`:

```powershell
$env:GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
.\scripts\deploy-cloud-run.ps1 -AllowUnauthenticated
```
