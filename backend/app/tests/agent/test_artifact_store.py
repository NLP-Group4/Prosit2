import uuid

from app.agent import artifact_store
from app.agent.artifacts import CodeFile


def test_store_and_load_code_bundle(tmp_path):
    artifact_store.ARTIFACT_STORE_ROOT = tmp_path
    run_id = uuid.uuid4()
    bundle_ref = artifact_store.store_code_bundle(
        run_id=run_id,
        stage="implementer",
        files=[CodeFile(path="app/main.py", content="print('ok')")],
        dependencies=["fastapi"],
    )

    payload = artifact_store.load_code_bundle(bundle_ref)

    assert payload is not None
    assert payload["dependencies"] == ["fastapi"]
    assert payload["files"] == [{"path": "app/main.py", "content": "print('ok')"}]
