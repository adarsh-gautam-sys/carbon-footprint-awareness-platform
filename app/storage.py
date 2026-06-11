import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def save_assessment(payload: dict[str, Any]) -> str:
    if os.getenv("FIRESTORE_ENABLED", "").lower() == "true":
        try:
            from google.cloud import firestore

            client = firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT") or None)
            doc_ref = client.collection("footprint_assessments").document(str(uuid4()))
            doc_ref.set({"created_at": datetime.now(UTC), **payload})
            return f"saved_to_firestore:{doc_ref.id}"
        except Exception as exc:
            return f"firestore_unavailable:{exc.__class__.__name__}"

    default_data_dir = Path(tempfile.gettempdir()) / "carbon-footprint-platform"
    data_dir = Path(os.getenv("LOCAL_DATA_DIR", str(default_data_dir)))
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "assessments.jsonl"
    record = {"id": str(uuid4()), "created_at": datetime.now(UTC).isoformat(), **payload}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    return f"saved_locally:{record['id']}"
