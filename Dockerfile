FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ── Security: create a non-root user ─────────────────────────────────────────
# Running as root in a container is a critical security misconfiguration.
# All file copies and the runtime process use the unprivileged 'appuser'.
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup --no-create-home appuser

WORKDIR /app

# Install dependencies before copying source for better layer caching
RUN pip install --no-cache-dir \
    fastapi==0.115.12 \
    "uvicorn[standard]==0.34.3" \
    pydantic==2.11.7 \
    pydantic-settings==2.7.0 \
    google-genai==1.0.0 \
    google-cloud-firestore==2.20.0 \
    google-cloud-logging==3.11.3 \
    cachetools==5.5.0 \
    httpx==0.28.1

# Copy application source with correct ownership
COPY --chown=appuser:appgroup app ./app
COPY --chown=appuser:appgroup static ./static

# Drop to non-root user for runtime
USER appuser

ENV PORT=8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
