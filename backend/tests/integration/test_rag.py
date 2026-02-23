import os
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

TEST_USER = {
    "email": "ragtest@example.com",
    "password": "ragtestpassword123"
}

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_rag(client: TestClient):
    # 1. Register/Login
    print("\n1. Authenticaton...")
    try:
        client.post("/auth/register", json=TEST_USER)
    except Exception as e:
        print("User might exist, ignoring register err")

    login_res = client.post(
        "/auth/login",
        data={"username": TEST_USER["email"], "password": TEST_USER["password"]}
    )
    login_res.raise_for_status()
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Logged in.")

    # 2. Upload Document
    print("\n2. Uploading specification document...")
    doc_content = """
[ARCHITECTURAL DECISION RECORD]
Project: Project Starbase
We need to build an API for the space station.
Core entities must follow these specific naming conventions:
- GalacticStarship: Must have a 'warp_speed' field (float) and 'captain_name' (string).
- AsteroidMiner: Must have 'mineral_yield_target' (integer) and 'active_status' (boolean).
"""
    with open("starbase_spec.txt", "w") as f:
        f.write(doc_content)
    
    with open("starbase_spec.txt", "rb") as f:
        files = {"file": ("starbase_spec.txt", f)}
        doc_res = client.post("/documents", headers=headers, files=files)
    
    doc_res.raise_for_status()
    print(f"Document uploaded: {doc_res.json()}")

    # 3. Request Generation using vague prompt
    print("\n3. Generating spec from a vague prompt (should use RAG context)...")
    prompt = "Build the space management API based on the document I just uploaded."
    
    gen_res = client.post(
        "/generate-from-prompt",
        headers=headers,
        json={"prompt": prompt, "model": "gemini-2.5-flash", "skip_verify": True}
    )
    
    if gen_res.status_code != 201:
        import json
        try:
            err_detail = json.dumps(gen_res.json(), indent=2)
        except:
            err_detail = gen_res.text
        pytest.fail(f"Generation failed with payload:\n{err_detail}")
        
    project_id = gen_res.json()["project_id"]
    print(f"Generated project {project_id}.")

    # 4. Verify the generated spec
    print("\n4. Verifying RAG influence on the generated spec...")
    proj_res = client.get(f"/projects/{project_id}", headers=headers)
    proj_res.raise_for_status()
    spec = proj_res.json()["spec"]
    
    entity_names = [e["name"] for e in spec["entities"]]
    print(f"Entities found: {entity_names}")
    
    assert "GalacticStarship" in entity_names, "The LLM did not use GalacticStarship from the RAG context."
    assert "AsteroidMiner" in entity_names, "The LLM did not use AsteroidMiner from the RAG context."
    print("✅ SUCCESS: The LLM read the uploaded document via RAG and used the specific entity names!")
