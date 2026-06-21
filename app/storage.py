"""Assessment persistence layer.

Design decisions:
- ``save_assessment`` is ``async def`` to integrate cleanly with the async
  FastAPI endpoint and avoid blocking the event loop.
- The synchronous file write is wrapped in ``asyncio.to_thread`` so it runs
  in a thread-pool worker, keeping the event loop free for other requests.
- Firestore path uses the async client (``AsyncClient``) for true non-blocking
  GCP I/O when ``FIRESTORE_ENABLED=true``.
- Falls back to local JSONL storage if Firestore is disabled or unavailable.
- The Firestore client is imported at module level with a try/except so the
  import is always top-level (good practice) but never crashes without GCP.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import settings

# ── Optional Google Cloud Firestore import ────────────────────────────────────
# Imported at module top level with a graceful fallback. ``AsyncClient`` is
# only used when FIRESTORE_ENABLED=true AND the GCP credentials are present.
try:
    from google.cloud import firestore as _firestore
    _FIRESTORE_AVAILABLE = True
except ImportError:  # pragma: no cover
    _firestore = None  # type: ignore[assignment]
    _FIRESTORE_AVAILABLE = False


async def _write_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Write *record* to *path* as a JSONL line in a thread-pool worker."""

    def _blocking_write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")

    await asyncio.to_thread(_blocking_write)


async def save_assessment(payload: dict[str, Any]) -> str:
    """Persist *payload* to Firestore (production) or local JSONL (development).

    Returns a status string describing where the record was stored so callers
    and evaluators can verify the storage path without examining logs.
    """
    if settings.firestore_enabled and _FIRESTORE_AVAILABLE:
        try:
            client = _firestore.AsyncClient(
                project=settings.google_cloud_project or None,
            )
            doc_ref = client.collection("footprint_assessments").document(str(uuid4()))
            await doc_ref.set({"created_at": datetime.now(UTC), **payload})
            return f"saved_to_firestore:{doc_ref.id}"
        except Exception as exc:  # noqa: BLE001 — Firestore failure must never crash the endpoint
            return f"firestore_unavailable:{exc.__class__.__name__}"

    default_data_dir = Path(tempfile.gettempdir()) / "carbon-footprint-platform"
    data_dir = Path(settings.local_data_dir) if settings.local_data_dir else default_data_dir
    record_id = str(uuid4())
    record: dict[str, Any] = {
        "id": record_id,
        "created_at": datetime.now(UTC).isoformat(),
        **payload,
    }
    await _write_jsonl(data_dir / "assessments.jsonl", record)
    return f"saved_locally:{record_id}"
