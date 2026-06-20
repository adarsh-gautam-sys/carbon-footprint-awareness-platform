# Antigravity Hackathon Master Playbook 🚀
**Goal:** Achieve 95%+ scores in AI/Cloud Hackathons across all grading rubrics.

> **To Antigravity (AI Agent):** Whenever you are tasked with building or optimizing a hackathon project, read this document first. This playbook outlines the exact architectural patterns, security standards, and Google Cloud integrations required to maximize scores in Code Quality, Security, Efficiency, Testing, Accessibility, and Google Services Integration.

---

## 1. Google Services Integration (Target: 100%)
To achieve maximum points, the project must demonstrate a meaningful, multi-layered integration of the Google Cloud ecosystem. Do not just use one API; use the stack.

*   **Compute (Cloud Run):** The backend MUST be a containerized FastAPI (Python) or Node.js app deployed to Google Cloud Run. Ensure the deployment is fully serverless and scalable.
*   **AI (Gemini + ADK):** Use the latest Gemini models (e.g., Gemini 2.5 Flash for speed). Always use the **Google Agent Development Kit (ADK)** or official `google-genai` SDK for orchestration, function calling (tools), and prompt management.
*   **Database (Firestore):** Use Google Cloud Firestore for session persistence, chat history, or application state. Ensure it is initialized gracefully (falling back to in-memory if credentials are missing locally).
*   **Observability (Cloud Logging):** Integrate the `google-cloud-logging` Python library to send structured logs to GCP. Do not rely solely on standard `print()` statements.
*   **Design (Stitch MCP):** If UI generation is required, leverage Google Stitch MCP to generate high-fidelity, Material-compliant design systems.

---

## 2. Security Standards (Target: 97%+)
Security is heavily scrutinized. Implement these defenses by default:

*   **Secret Management:** NO API keys in the codebase. Ever. Use `.env` files locally and strict Environment Variables on Cloud Run.
*   **Git & Docker Hygiene:** Ensure `.gitignore` and `.dockerignore` strictly exclude `.venv`, `.env`, `__pycache__`, and any `*-adminsdk-*.json` (Firebase Service Accounts).
*   **Container Security:** The `Dockerfile` MUST run the application as a **non-root user** (e.g., `appuser`).
*   **Security Headers:** The backend must attach strict HTTP headers:
    *   `X-Content-Type-Options: nosniff`
    *   `X-Frame-Options: DENY`
    *   `X-XSS-Protection: 1; mode=block`
    *   `Referrer-Policy: strict-origin-when-cross-origin`
*   **CORS:** Implement strict CORS middleware. Never use `allow_origins=["*"]` in production. Explicitly list the local dev ports and the Cloud Run domain.

---

## 3. Efficiency & Performance (Target: 100%)
The app must be fast and respectful of API quotas.

*   **Caching Layer:** Implement an aggressive caching layer (e.g., Python `cachetools.TTLCache`) for LLM responses. Pre-seed the cache on startup with expected demo queries to achieve 0ms latency and 0 API cost for common questions.
*   **Rate Limiting:** Implement `asyncio.Semaphore` to cap concurrent LLM calls (e.g., max 3) to prevent `429 Resource Exhausted` errors on free-tier API keys.
*   **Asynchronous I/O:** All FastAPI endpoints, database calls, and LLM network requests must use `async`/`await`.

---

## 4. Code Quality & Structure (Target: 90%+)
The repository must look like it was written by a Senior Engineer.

*   **Modularity:** Split the backend logically:
    *   `main.py` (API, Middleware, Lifespan)
    *   `config.py` (Pydantic Settings)
    *   `agent.py` (ADK Agent definition)
    *   `tools.py` (Function definitions)
    *   `cache.py` / `database.py`
*   **Typing:** Strict Python type hints (`-> dict[str, Any]`, `list[str]`) on every function.
*   **Documentation:** Comprehensive docstrings. A highly detailed `README.md` containing an Architecture Diagram, Setup Instructions, and a dedicated "Google Services Used" table.
*   **Repository Size:** Keep the `.git` footprint tiny (< 5MB). Scrub large binary files (`.zip`, `.venv`) from the history before submission.

---

## 5. Testing (Target: 95%+)
Do not submit without automated tests.

*   **Framework:** Use `pytest`.
*   **Coverage:** 
    *   `test_tools.py`: Unit test every AI tool for expected structured output.
    *   `test_api.py`: Integration test the FastAPI endpoints using `TestClient`.
    *   `test_config.py`: Verify that environment variables load correctly.
*   **CI/CD Readiness:** The tests must pass completely locally before pushing.

---

## 6. Accessibility & UI (Target: 98%+)
The frontend must be inclusive and flawlessly designed.

*   **Semantic HTML:** Use `<main>`, `<header>`, `<footer>`, `<nav>`, `<article>`.
*   **ARIA Attributes:** Every interactive element must have `aria-label`, `role="dialog"` (for modals), and `aria-hidden="true"` (for decorative icons).
*   **Keyboard Navigation:** The app must be fully navigable using `Tab`, `Space`, and `Enter`. Add focus rings (`focus:ring-2`) to interactive elements.
*   **Aesthetics:** Use a premium design system (e.g., Tailwind CSS, dark glassmorphism, modern typography like 'Outfit' or 'Inter'). Avoid default browser styling completely.

---

### Implementation Workflow for Antigravity
When asked to start a new hackathon project based on this playbook:
1. **Scaffold:** Set up the modular directory structure and strict `.gitignore`.
2. **Backend:** Write the FastAPI server with all security middleware and Cloud Logging.
3. **Agent:** Define the ADK tools and Gemini models.
4. **Testing:** Write the `pytest` suite and ensure 100% pass rate.
5. **Frontend:** Build an ARIA-compliant, highly polished UI.
6. **Deploy:** Create the non-root Dockerfile and provide the `gcloud run deploy` command.
7. **Clean:** Verify the total repository size is minimal before the final Git push.
