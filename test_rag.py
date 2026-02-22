import os
import time
import requests

API_URL = "http://localhost:8000"
TEST_USER = {
    "email": "ragtest@example.com",
    "password": "ragtestpassword123"
}

def wait_for_api():
    print("Waiting for API to be ready...")
    for _ in range(30):
        try:
            res = requests.get(f"{API_URL}/health")
            if res.status_code == 200:
                print("API is ready.")
                return
        except:
            pass
        time.sleep(1)
    raise RuntimeError("API did not start in time.")

def test_rag():
    wait_for_api()

    # 1. Register/Login
    print("\n1. Authenticaton...")
    try:
        requests.post(f"{API_URL}/auth/register", json=TEST_USER)
    except Exception as e:
        print("User might exist, ignoring register err")

    login_res = requests.post(
        f"{API_URL}/auth/login",
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
        doc_res = requests.post(f"{API_URL}/documents", headers=headers, files=files)
    
    doc_res.raise_for_status()
    print(f"Document uploaded: {doc_res.json()}")

    # 3. Request Generation using vague prompt
    print("\n3. Generating spec from a vague prompt (should use RAG context)...")
    prompt = "Build the space management API based on the document I just uploaded."
    
    gen_res = requests.post(
        f"{API_URL}/generate-from-prompt",
        headers=headers,
        json={"prompt": prompt, "model": "gemini-2.5-flash", "skip_verify": True}
    )
    
    if gen_res.status_code != 201:
        print(f"Generation failed: {gen_res.text}")
        return
        
    project_id = gen_res.json()["project_id"]
    print(f"Generated project {project_id}.")

    # 4. Verify the generated spec
    print("\n4. Verifying RAG influence on the generated spec...")
    proj_res = requests.get(f"{API_URL}/projects/{project_id}", headers=headers)
    proj_res.raise_for_status()
    spec = proj_res.json()["spec"]
    
    entity_names = [e["name"] for e in spec["entities"]]
    print(f"Entities found: {entity_names}")
    
    if "GalacticStarship" in entity_names and "AsteroidMiner" in entity_names:
        print("✅ SUCCESS: The LLM read the uploaded document via RAG and used the specific entity names!")
    else:
        print("❌ FAILURE: The LLM did not use the entity names from the document.")

if __name__ == "__main__":
    test_rag()
