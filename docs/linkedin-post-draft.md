# LinkedIn Post Draft

I built a Carbon Footprint Awareness Platform for PromptWars 2026 Challenge 3.

The goal is simple: help individuals understand, track, and reduce their carbon footprint through practical actions and personalized insights.

What I used:

- Gemini API for concise, personalized recommendations.
- FastAPI for a clean backend and structured API responses.
- Google Cloud Run for deployment.
- Secret Manager for API keys.
- Optional Firestore for assessment history.
- Sequential Thinking MCP for structured planning and review checkpoints.

What I learned:

- A useful AI agent needs reliable deterministic logic, not only LLM output.
- Carbon advice is more effective when it starts with small, measurable actions.
- Fallback paths matter because demos and deployments should still work without optional services.
- Documentation, testing, and deployment readiness are part of the product, not extras.

The platform estimates impact across home energy, transport, food, and lifestyle, then ranks actions by estimated monthly CO2e savings.
