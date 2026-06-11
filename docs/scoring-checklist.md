# PromptWars Scoring Checklist

## 1. Problem Definition

- Real problem: people lack clear, personal, actionable carbon footprint guidance.
- Target users: individuals, families, students, and community programs.
- AI necessity: personalized interpretation and recommendation wording.

## 2. AI Agent Capabilities

- Understands structured user input.
- Breaks emissions into home, transport, and lifestyle categories.
- Selects actions by estimated impact.
- Executes storage and insight generation.
- Produces structured JSON and readable UI output.
- Includes fallback behavior when Gemini or Firestore is unavailable.

## 3. System Architecture

- Frontend/input layer: `static/`.
- Backend/API layer: `app/main.py`.
- LLM layer: `app/insights.py`.
- Tool execution layer: `app/carbon.py`.
- Storage layer: `app/storage.py`.
- Deployment: `Dockerfile`, Cloud Run script, and Cloud Run docs.

## 4. Code Assessment Criteria

- Code quality: modular Python package with separated models, calculations, insights, and storage.
- Security: no hardcoded secrets; `.env` ignored; Secret Manager documented.
- Efficiency: deterministic calculations minimize LLM calls; Gemini is used only for final phrasing.
- Testing: unit tests cover calculations, action generation, confidence bounds, and fallback insights.
- Accessibility: labels, readable contrast, responsive layout, and live status region.
- Problem alignment: every input and output maps to carbon awareness and reduction.
- Google services: Gemini, Cloud Run, Cloud Build, Artifact Registry, Secret Manager, optional Firestore.

## 5. Validation Requirements

- Architecture diagram: `docs/architecture.md`.
- Tool usage explanation: `docs/tool-usage.md`.
- Prompt flow explanation: `docs/prompt-engineering.md`.
- Screenshots can be captured after running the app locally.
- LinkedIn post draft can be created from the tool usage and architecture docs.
