param(
  [string]$ProjectId = $env:GOOGLE_CLOUD_PROJECT,
  [string]$Region = $(if ($env:GOOGLE_CLOUD_REGION) { $env:GOOGLE_CLOUD_REGION } else { "us-central1" }),
  [string]$Service = $(if ($env:CLOUD_RUN_SERVICE) { $env:CLOUD_RUN_SERVICE } else { "promptwars-agent" }),
  [string]$Source = ".",
  [switch]$AllowUnauthenticated
)

$ErrorActionPreference = "Stop"

if (-not $ProjectId) {
  throw "ProjectId is required. Pass -ProjectId or set GOOGLE_CLOUD_PROJECT."
}

function Require-Command($Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command '$Name' was not found. Install Google Cloud CLI and retry."
  }
}

Require-Command "gcloud"

gcloud config set project $ProjectId | Out-Null
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

$authFlag = if ($AllowUnauthenticated) { "--allow-unauthenticated" } else { "--no-allow-unauthenticated" }

gcloud run deploy $Service `
  --source $Source `
  --region $Region `
  --platform managed `
  --port 8080 `
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$ProjectId,GOOGLE_CLOUD_REGION=$Region" `
  $authFlag

gcloud run services describe $Service `
  --region $Region `
  --format "value(status.url)"
