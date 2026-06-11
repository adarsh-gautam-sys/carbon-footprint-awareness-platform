# Prompt Engineering Process

## Initial Prompt

```text
Explain this user's carbon footprint and suggest ways to reduce it.
```

Issue: Too broad, likely to produce generic advice and unsupported assumptions.

## Iteration 1

```text
Given category totals and candidate actions, write practical recommendations.
```

Improvement: Grounds the model in calculated data, but output format is still inconsistent.

## Iteration 2

```text
Return exactly 3 short bullet-style insights. Each insight must be under 28 words.
Use only the provided footprint numbers and candidate actions.
```

Improvement: Adds predictable output, avoids hallucinated claims, and keeps the UI readable.

## Final Prompt Strategy

The final implementation in `app/insights.py` separates:

- System instruction: role, tone, safety boundaries.
- User prompt: validated profile, category totals, and candidate actions.
- Output constraint: exactly three short insights.

## Final System Instruction

```text
You are a carbon footprint coach.
Give concise, practical, non-judgmental advice.
Avoid guilt, politics, and unsupported claims.
Personalize recommendations from the provided footprint numbers only.
```

## Reliability Choice

Gemini enhances personalization, but the app remains fully functional without Gemini by using deterministic fallback insights. This improves demo reliability and avoids failing if an API key is unavailable.
