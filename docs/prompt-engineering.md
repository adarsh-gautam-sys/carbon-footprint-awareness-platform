# Prompt Engineering Process

## Problem With Naive Prompting

An initial naive prompt ("Explain this user's carbon footprint and suggest ways to reduce it") produces:

- Generic advice not grounded in the user's actual data
- Hallucinated statistics and unsupported claims
- Inconsistent output formats that break the UI
- Guilt-inducing or politically charged language that reduces engagement

## Iteration 1 — Ground in Data

```text
Given category totals and candidate actions, write practical recommendations.
```

**Problem:** Output format inconsistent. Model sometimes adds context not in the data.

## Iteration 2 — Add Output Constraints

```text
Return exactly 3 short bullet-style insights. Each insight must be under 28 words.
Use only the provided footprint numbers and candidate actions.
```

**Improvement:** Predictable output length. Still occasionally adds unsupported context.

## Iteration 3 — Separate System and User Prompt

Split into:
- **System instruction** — role, tone, and strict safety boundaries
- **User prompt** — structured data (profile, totals, categories, actions)
- **Output constraint** — exactly 3 plain sentences, ≤32 words each

**Improvement:** System instruction controls guardrails. User prompt grounds the model. Output constraint keeps the UI readable.

## Final System Instruction

```text
You are a carbon footprint coach for an AI awareness platform.
Your role: give concise, practical, non-judgmental carbon reduction advice.
Rules you must follow:
- Use ONLY the footprint numbers and actions provided. Do not invent data.
- Avoid guilt, politics, blame, and unsupported scientific claims.
- Personalise each insight using the user's name, country, and primary goal.
- Be specific: reference actual kg values and action titles from the input.
- Keep advice motivating and achievable, not overwhelming.
```

**Why this works:**
- "ONLY the footprint numbers" prevents hallucination
- Listing specific rule violations (guilt, politics, blame) prevents the most common failure modes
- "Reference actual kg values" forces grounding in the validated data
- "Not overwhelming" steers tone without over-constraining wording

## Final User Prompt Structure

```
User profile:
- Name: {name}
- Country: {country}
- Primary goal: {goal}

Estimated monthly carbon footprint:
- Total: {total} kg CO2e/month ({yearly} tonnes/year)
{per-category breakdown with explanations}

Top recommended actions:
{ranked actions with savings and effort}

Task: Return EXACTLY 3 concise insights as plain sentences (no markdown).
Each insight must:
1. Be under 32 words.
2. Reference specific numbers or action titles from the data above.
3. Be personalised using the user's name or goal where natural.
4. Be motivating and practical, not guilt-inducing.
```

## Temperature Choice

`temperature=0.25` — Low enough to keep outputs consistent and grounded; high enough to avoid repetitive phrasing across users with similar profiles.

## Reliability Design

Gemini enhances personalisation but the app is fully functional without it. If the API key is missing, the network fails, or Gemini returns fewer than 2 usable sentences, the platform falls back to three deterministic insights that:

1. Name the user's largest emission category with exact kg values
2. State the top recommended action with its estimated monthly saving
3. Reference the 2-tonne Paris 1.5°C target for motivating context

This ensures the demo and production service always work regardless of external API availability.
