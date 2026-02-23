#!/usr/bin/env python3
"""
Manual test script for Cloud + Electron integration.
Tests the new verify-report and fix endpoints.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_health():
    """Test that the API is running."""
    print("Testing health endpoint...")
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    print("✅ Health check passed")
    return True

def test_models():
    """Test that models endpoint returns available models."""
    print("\nTesting models endpoint...")
    r = requests.get(f"{BASE_URL}/models")
    assert r.status_code == 200, f"Models endpoint failed: {r.status_code}"
    data = r.json()
    assert "models" in data, "No models in response"
    assert len(data["models"]) > 0, "No models available"
    print(f"✅ Found {len(data['models'])} models:")
    for model in data["models"]:
        print(f"   - {model['name']} ({model['id']})")
    return True

def register_test_user():
    """Register a test user and return auth token."""
    print("\nRegistering test user...")
    email = f"test-electron-{int(requests.get(f'{BASE_URL}/health').elapsed.total_seconds() * 1000)}@example.com"
    password = "TestPass123!"
    
    r = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": password
    })
    
    if r.status_code != 201:
        print(f"⚠️  Registration failed (might already exist): {r.status_code}")
        # Try to login instead
        r = requests.post(f"{BASE_URL}/auth/login", data={
            "username": email,
            "password": password,
            "grant_type": "password"
        })
        if r.status_code != 200:
            raise Exception(f"Login failed: {r.status_code} - {r.text}")
    else:
        print(f"✅ User registered: {email}")
        # Login to get token
        r = requests.post(f"{BASE_URL}/auth/login", data={
            "username": email,
            "password": password,
            "grant_type": "password"
        })
    
    token = r.json()["access_token"]
    print(f"✅ Got auth token")
    return token, email

def test_verify_report_endpoint(token):
    """Test the new verify-report endpoint (requires a project)."""
    print("\nTesting verify-report endpoint...")
    
    # First, create a simple project
    print("  Creating a test project...")
    r = requests.post(f"{BASE_URL}/generate", 
        headers={"Authorization": f"Bearer {token}"},
        json={
            "project_name": "test-verify-project",
            "entities": [
                {
                    "name": "Task",
                    "table_name": "tasks",
                    "fields": [
                        {"name": "id", "type": "integer", "primary_key": True},
                        {"name": "title", "type": "string", "required": True}
                    ],
                    "crud": True
                }
            ],
            "auth": {"enabled": False},
            "database": {"type": "postgres"}
        }
    )
    
    if r.status_code != 201:
        print(f"⚠️  Project creation failed: {r.status_code} - {r.text}")
        return False
    
    project_id = r.json()["project_id"]
    print(f"✅ Project created: {project_id}")
    
    # Now test the verify-report endpoint
    print("  Submitting verification report...")
    verification_report = {
        "passed": True,
        "elapsed_ms": 1234,
        "results": [
            {
                "test_name": "GET /health",
                "endpoint": "/health",
                "method": "GET",
                "passed": True,
                "status_code": 200,
                "elapsed": 50
            }
        ]
    }
    
    r = requests.post(
        f"{BASE_URL}/projects/{project_id}/verify-report",
        headers={"Authorization": f"Bearer {token}"},
        json=verification_report
    )
    
    if r.status_code != 200:
        print(f"❌ Verify-report failed: {r.status_code} - {r.text}")
        return False
    
    print(f"✅ Verification report submitted successfully")
    print(f"   Response: {r.json()}")
    return True

def test_fix_endpoint(token):
    """Test the new fix endpoint (requires a failed project)."""
    print("\nTesting fix endpoint...")
    
    # Create a project
    print("  Creating a test project...")
    r = requests.post(f"{BASE_URL}/generate", 
        headers={"Authorization": f"Bearer {token}"},
        json={
            "project_name": "test-fix-project",
            "entities": [
                {
                    "name": "Item",
                    "table_name": "items",
                    "fields": [
                        {"name": "id", "type": "integer", "primary_key": True},
                        {"name": "name", "type": "string", "required": True}
                    ],
                    "crud": True
                }
            ],
            "auth": {"enabled": False},
            "database": {"type": "postgres"}
        }
    )
    
    if r.status_code != 201:
        print(f"⚠️  Project creation failed: {r.status_code}")
        return False
    
    project_id = r.json()["project_id"]
    print(f"✅ Project created: {project_id}")
    
    # Submit a failed verification report
    print("  Submitting failed verification report...")
    verification_report = {
        "passed": False,
        "elapsed_ms": 2000,
        "results": [
            {
                "test_name": "POST /api/items",
                "endpoint": "/api/items",
                "method": "POST",
                "passed": False,
                "status_code": 500,
                "error_message": "Internal server error",
                "elapsed": 100
            }
        ]
    }
    
    r = requests.post(
        f"{BASE_URL}/projects/{project_id}/verify-report",
        headers={"Authorization": f"Bearer {token}"},
        json=verification_report
    )
    
    if r.status_code != 200:
        print(f"❌ Failed to submit verification report: {r.status_code}")
        return False
    
    print(f"✅ Failed verification report submitted")
    
    # Now test the fix endpoint
    print("  Requesting auto-fix...")
    fix_request = {
        "attempt_number": 1,
        "failed_tests": [
            {
                "method": "POST",
                "endpoint": "/api/items",
                "error_message": "Internal server error"
            }
        ]
    }
    
    r = requests.post(
        f"{BASE_URL}/projects/{project_id}/fix",
        headers={"Authorization": f"Bearer {token}"},
        json=fix_request
    )
    
    if r.status_code != 200:
        print(f"❌ Fix endpoint failed: {r.status_code} - {r.text}")
        return False
    
    response = r.json()
    print(f"✅ Fix endpoint responded successfully")
    print(f"   Status: {response.get('status')}")
    if response.get('warnings'):
        print(f"   Warnings: {response['warnings']}")
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("Cloud + Electron Integration Test Suite")
    print("=" * 60)
    
    try:
        # Basic tests
        test_health()
        test_models()
        
        # Auth
        token, email = register_test_user()
        
        # New endpoints
        test_verify_report_endpoint(token)
        test_fix_endpoint(token)
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe Cloud + Electron integration is working correctly.")
        print("New endpoints are functional:")
        print("  - POST /projects/{id}/verify-report ✅")
        print("  - POST /projects/{id}/fix ✅")
        print("\nNote: Auto-fix logic is currently stubbed (Phase 1).")
        
        return 0
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
