import json
import logging
import uuid
from pathlib import Path
from typing import Any

from app.agent.artifacts import CodeFile

logger = logging.getLogger(__name__)

ARTIFACT_STORE_ROOT = Path(__file__).resolve().parents[2] / "artifact_store"


def _ensure_store_root() -> Path:
    ARTIFACT_STORE_ROOT.mkdir(parents=True, exist_ok=True)
    return ARTIFACT_STORE_ROOT


def _bundle_filename(run_id: uuid.UUID, stage: str) -> str:
    safe_stage = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in stage)
    return f"{run_id}_{safe_stage}.json"


def store_code_bundle(
    *,
    run_id: uuid.UUID,
    stage: str,
    files: list[CodeFile] | list[dict[str, Any]],
    dependencies: list[str] | None = None,
) -> str:
    store_root = _ensure_store_root()
    bundle_path = store_root / _bundle_filename(run_id, stage)
    payload = {
        "files": [
            file.model_dump() if isinstance(file, CodeFile) else dict(file)
            for file in files
        ],
        "dependencies": list(dependencies or []),
    }
    bundle_path.write_text(json.dumps(payload), encoding="utf-8")
    return bundle_path.name


def load_code_bundle(bundle_ref: str) -> dict[str, Any] | None:
    if not bundle_ref:
        return None

    bundle_path = _ensure_store_root() / Path(bundle_ref).name
    if not bundle_path.exists():
        logger.warning("Artifact bundle not found: %s", bundle_path)
        return None

    try:
        return json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load artifact bundle %s: %s", bundle_path, exc)
        return None

