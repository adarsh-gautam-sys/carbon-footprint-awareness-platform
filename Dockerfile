FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.137.1 \
    "uvicorn[standard]==0.34.0" \
    pydantic==2.10.4 \
    google-genai==1.0.0 \
    google-cloud-firestore==2.20.0 \
    pytest==9.1.0 \
    httpx==0.28.1

COPY app ./app
COPY static ./static

ENV PORT=8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
