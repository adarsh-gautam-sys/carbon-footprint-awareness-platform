# PromptWars 2026 Scoring Checklist

## 1. Problem Definition ✅

- [x] Real-world problem: individuals lack clear, personal, actionable carbon footprint guidance.
- [x] Target users defined: individuals, families, students, community programmes.
- [x] Why AI is necessary: personalised phrasing, goal-aware prioritisation, motivational framing.
- [x] Real-world applicability: transparent emission factors from IPCC/EPA/DEFRA; referenced in code.

## 2. AI Agent Capabilities ✅

- [x] Understands structured user input (Pydantic validation).
- [x] Breaks emissions into three distinct categories (home, transport, lifestyle).
- [x] Selects actions based on calculated impact thresholds.
- [x] Executes storage (Firestore or local JSONL) and insight generation.
- [x] Produces structured JSON (OpenAPI-documented) and readable web UI.
- [x] Multi-step reasoning: validate → calculate → rank → personalise → store.
- [x] Fallback mechanism: deterministic insights when Gemini is unavailable.
- [x] Confidence scoring: transparent estimate quality indicator.

## 3. System Architecture ✅

- [x] Frontend/input layer: `static/` — responsive HTML, CSS, JS with educational content.
- [x] Backend/API layer: `app/main.py` — FastAPI with OpenAPI schema.
- [x] LLM layer: `app/insights.py` — Gemini adapter with system instruction.
- [x] Tool execution layer: `app/carbon.py` — factor-based calculations and action ranking.
- [x] Storage layer: `app/storage.py` — Firestore (prod) or local JSONL (dev).
- [x] Deployment: `Dockerfile`, Cloud Run script, service YAML.
- [x] Architecture diagram: in `docs/architecture.md` (Mermaid + ASCII).
- [x] Data flow explanation: 10-step agent decision logic documented.
- [x] Tool invocation logic: clearly documented in architecture and tool-usage docs.

## 4. Code Assessment Criteria ✅

- [x] **Code quality**: modular Python package (models, carbon, insights, storage, main).
- [x] **Security**: no hardcoded secrets; `.env.example` provided; `.env` in `.gitignore`; Secret Manager documented; CORS configurable via env var.
- [x] **Efficiency**: deterministic calculations minimise LLM calls; Gemini called once per request only for phrasing; `max_output_tokens=256` caps cost.
- [x] **Testing**: 41 tests across unit, integration, edge case, and boundary categories; all pass.
- [x] **Accessibility**: skip link, semantic HTML, ARIA labels, `role="status"` live region, focus styles, responsive layout, field hints, high-contrast media query.
- [x] **Problem alignment**: every input field and output value maps to carbon awareness or reduction.
- [x] **Google services**: Gemini API, Cloud Run, Cloud Build, Artifact Registry, Secret Manager, Firestore.

## 5. Documentation ✅

- [x] Tool usage explanation: `docs/tool-usage.md` — all tools and justifications.
- [x] Prompt engineering process: `docs/prompt-engineering.md` — 4 iterations with reasoning.
- [x] Architecture documentation: `docs/architecture.md` — flow diagram, components table, decision logic.
- [x] Human vs AI responsibilities: `docs/human-ai-responsibilities.md`.
- [x] Deployment guide: `docs/google-cloud-run.md`.
- [x] LinkedIn post draft: `docs/linkedin-post-draft.md`.
- [x] README: feature table, config reference, architecture overview, emission sources.
- [x] Environment variables: fully documented in `docs/tool-usage.md` and README.

## 6. Validation Requirements ✅

- [x] Architecture diagram: `docs/architecture.md`.
- [x] Tool usage explanation: `docs/tool-usage.md`.
- [x] Prompt flow explanation: `docs/prompt-engineering.md`.
- [x] LinkedIn post draft: `docs/linkedin-post-draft.md`.
- [ ] Screenshots: capture after running `uvicorn app.main:app --reload` locally.

## 7. Sustainability Impact ✅

- [x] Educational content: footer explains CO₂e, Paris target, and methodology.
- [x] Global comparison: user footprint vs India average, world average, Paris 1.5°C target.
- [x] Actionable recommendations: ranked by impact, labelled by effort, with clear reasoning.
- [x] Personalisation: Gemini insights reference the user's name, goal, and exact kg values.
- [x] Progress framing: third fallback insight references the 2-tonne Paris target for motivation.
- [x] Methodology transparency: emission factor sources cited in code and README.
