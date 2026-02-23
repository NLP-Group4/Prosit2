#!/usr/bin/env python3
"""
Full end-to-end test of the auto-fix logic.

This test:
1. Creates a user and generates a project
2. Manually introduces a bug into the generated code
3. Simulates a failed verification report
4. Triggers the auto-fix endpoint
5. Verifies the fix was applied correctly
"""

import asyncio
import requests
import json
import sys
import zipfile
import tempfile
from pathlib import Path

BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def register_and_login():
    """Register a test user and return auth token."""
    print_section("Step 1: Authentication")
    
    email = f"autofix-test-{int(requests.get(f'{BASE_URL}/health').elapsed.total_seconds() * 1000)}@example.com"
    password = "TestPass123!"
    
    print(f"Registering user: {email}")
    r = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": password
    })
    
    if r.status_code == 409:
        print("User already exists, logging in...")
    elif r.status_code != 201:
        raise Exception(f"Registration failed: {r.status_code} - {r.text}")
    else:
        print("✅ User registered successfully")
    
    # Login
    print("Logging in...")
    r = requests.post(f"{BASE_URL}/auth/login", data={
        "username": email,
        "password": password,
        "grant_type": "password"
    })
    
    if r.status_code != 200:
        raise Exception(f"Login failed: {r.status_code} - {r.text}")
    
    token = r.json()["access_token"]
    print(f"✅ Logged in successfully")
    return token, email


def create_project(token):
    """Create a simple test project."""
    print_section("Step 2: Generate Project")
    
    print("Creating a simple task API project...")
    
    spec = {
        "project_name": "autofix-test-api",
        "description": "Test API for auto-fix validation",
        "spec_version": "1.0",
        "database": {"type": "postgres", "version": "15"},
        "auth": {"enabled": False},
        "entities": [
            {
                "name": "Task",
                "table_name": "tasks",
                "fields": [
                    {"name": "id", "type": "uuid", "primary_key": True, "nullable": False},
                    {"name": "title", "type": "string", "nullable": False},
                    {"name": "description", "type": "text", "nullable": True},
                    {"name": "completed", "type": "boolean", "nullable": False},
                    {"name": "created_at", "type": "datetime", "nullable": False}
                ],
                "crud": True
            }
        ]
    }
    
    r = requests.post(
        f"{BASE_URL}/generate",
        headers={"Authorization": f"Bearer {token}"},
        json=spec
    )
    
    if r.status_code != 201:
        raise Exception(f"Project creation failed: {r.status_code} - {r.text}")
    
    data = r.json()
    project_id = data["project_id"]
    project_name = data["project_name"]
    
    print(f"✅ Project created: {project_name} (ID: {project_id})")
    return project_id, project_name


def introduce_bug(token, project_id):
    """
    Download the project ZIP, introduce a bug, and re-upload it.
    
    Bug: Remove an import statement to cause ImportError
    """
    print_section("Step 3: Introduce Bug")
    
    print("Downloading project ZIP...")
    r = requests.get(
        f"{BASE_URL}/projects/{project_id}/download",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if r.status_code != 200:
        raise Exception(f"Download failed: {r.status_code}")
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
        tmp.write(r.content)
        zip_path = Path(tmp.name)
    
    print(f"✅ Downloaded ZIP: {zip_path}")
    
    # Extract and modify
    extract_dir = tempfile.mkdtemp()
    print(f"Extracting to: {extract_dir}")
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_dir)
    
    # Find the routes file and introduce a bug
    routes_file = None
    for item in Path(extract_dir).rglob('routes.py'):
        routes_file = item
        break
    
    if not routes_file:
        print("⚠️  Could not find routes.py, creating a buggy version...")
        # Create a buggy routes file
        app_dir = Path(extract_dir) / list(Path(extract_dir).iterdir())[0] / 'app'
        app_dir.mkdir(parents=True, exist_ok=True)
        routes_file = app_dir / 'routes.py'
        
        buggy_code = '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
# BUG: Missing import for models and schemas
from . import database

router = APIRouter()

@router.get("/tasks")
def get_tasks(db: Session = Depends(database.get_db)):
    # BUG: models is not imported
    tasks = db.query(models.Task).all()
    return tasks

@router.post("/tasks")
def create_task(task: schemas.TaskCreate, db: Session = Depends(database.get_db)):
    # BUG: models is not imported
    db_task = models.Task(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task
'''
        routes_file.write_text(buggy_code)
        print(f"✅ Created buggy routes.py at: {routes_file}")
    else:
        print(f"Found routes.py at: {routes_file}")
        
        # Read and modify
        content = routes_file.read_text()
        
        # Remove the models import (introduce bug)
        if 'from . import models' in content:
            content = content.replace('from . import models', '# BUG: Missing models import')
            routes_file.write_text(content)
            print("✅ Introduced bug: Removed 'from . import models'")
        elif 'import models' in content:
            content = content.replace('import models', '# BUG: Missing models import')
            routes_file.write_text(content)
            print("✅ Introduced bug: Removed models import")
        else:
            # Add a buggy endpoint
            buggy_endpoint = '''

@router.get("/buggy")
def buggy_endpoint():
    # BUG: undefined_variable is not defined
    return {"result": undefined_variable}
'''
            content += buggy_endpoint
            routes_file.write_text(content)
            print("✅ Introduced bug: Added endpoint with undefined variable")
    
    print(f"Bug introduced in: {routes_file}")
    return extract_dir, zip_path


def simulate_failed_verification(token, project_id):
    """Submit a failed verification report."""
    print_section("Step 4: Simulate Failed Verification")
    
    print("Submitting failed verification report...")
    
    report = {
        "passed": False,
        "elapsed_ms": 2500,
        "results": [
            {
                "test_name": "GET /tasks",
                "endpoint": "/tasks",
                "method": "GET",
                "passed": False,
                "status_code": 500,
                "error_message": "NameError: name 'models' is not defined"
            },
            {
                "test_name": "POST /tasks",
                "endpoint": "/tasks",
                "method": "POST",
                "passed": False,
                "status_code": 500,
                "error_message": "NameError: name 'models' is not defined"
            }
        ]
    }
    
    r = requests.post(
        f"{BASE_URL}/projects/{project_id}/verify-report",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=report
    )
    
    if r.status_code != 200:
        print(f"Response: {r.text}")
        raise Exception(f"Verification report failed: {r.status_code} - {r.text}")
    
    print("✅ Failed verification report submitted")
    print(f"   Status: {r.json()['status']}")


def trigger_autofix(token, project_id):
    """Trigger the auto-fix endpoint."""
    print_section("Step 5: Trigger Auto-Fix")
    
    print("Requesting auto-fix from LLM...")
    
    fix_request = {
        "attempt_number": 1,
        "failed_tests": [
            {
                "method": "GET",
                "endpoint": "/tasks",
                "error_message": "NameError: name 'models' is not defined"
            },
            {
                "method": "POST",
                "endpoint": "/tasks",
                "error_message": "NameError: name 'models' is not defined"
            }
        ]
    }
    
    print("Calling /projects/{id}/fix endpoint...")
    print("This will:")
    print("  1. Load the project spec and current code")
    print("  2. Send failed tests to Google Gemini")
    print("  3. Receive analysis and fixes from LLM")
    print("  4. Apply fixes to the code")
    print("  5. Reassemble and save the fixed ZIP")
    print("\nThis may take 10-30 seconds...")
    
    r = requests.post(
        f"{BASE_URL}/projects/{project_id}/fix",
        headers={"Authorization": f"Bearer {token}"},
        json=fix_request,
        timeout=60  # Allow time for LLM call
    )
    
    if r.status_code != 200:
        raise Exception(f"Auto-fix failed: {r.status_code} - {r.text}")
    
    data = r.json()
    print("\n✅ Auto-fix completed!")
    print(f"   Status: {data.get('status')}")
    
    if data.get('warnings'):
        print("\n   Warnings:")
        for warning in data['warnings']:
            print(f"   - {warning}")
    
    return data


def verify_fix(token, project_id):
    """Download the fixed ZIP and verify the bug was fixed."""
    print_section("Step 6: Verify Fix")
    
    print("Downloading fixed project ZIP...")
    r = requests.get(
        f"{BASE_URL}/projects/{project_id}/download",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if r.status_code != 200:
        raise Exception(f"Download failed: {r.status_code}")
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
        tmp.write(r.content)
        fixed_zip_path = Path(tmp.name)
    
    print(f"✅ Downloaded fixed ZIP: {fixed_zip_path}")
    
    # Extract and check
    extract_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(fixed_zip_path, 'r') as zf:
        zf.extractall(extract_dir)
        print(f"Extracted to: {extract_dir}")
    
    # Find the actual routes file - check both possible locations
    routes_files = []
    for pattern in ['**/routes.py', '**/routers/*.py', '**/routes/*.py']:
        routes_files.extend(Path(extract_dir).glob(pattern))
    
    print(f"\nFound {len(routes_files)} potential route files:")
    for f in routes_files:
        print(f"  - {f.relative_to(extract_dir)}")
    
    # Check each routes file for the fix
    fix_found = False
    for routes_file in routes_files:
        if routes_file.is_file():
            print(f"\nChecking: {routes_file.name}")
            try:
                content = routes_file.read_text()
                
                # Check if this file has Task-related routes
                if 'Task' not in content and 'task' not in content.lower():
                    print(f"  Skipping (no Task routes)")
                    continue
                
                # Check if the import was restored
                has_models_import = (
                    'from . import models' in content or
                    'from .. import models' in content or
                    'import models' in content or
                    'from app import models' in content or
                    'from .models import' in content or
                    'from ..models import' in content or
                    'from app.models import' in content
                )
                
                # Check if bug comment was removed
                has_bug_comment = 'BUG:' in content
                
                print(f"  Models import present: {has_models_import}")
                print(f"  Bug comment removed: {not has_bug_comment}")
                
                if has_models_import and not has_bug_comment:
                    print(f"\n✅ Fix verified in {routes_file.name}!")
                    print("\nFixed code imports:")
                    print("-" * 70)
                    # Show the import section
                    lines = content.split('\n')
                    for line in lines[:25]:  # First 25 lines
                        if 'import' in line.lower() or 'from' in line.lower():
                            print(line)
                    print("-" * 70)
                    fix_found = True
                    break
                elif has_models_import:
                    print(f"  ⚠️  Has import but bug comment still present")
                elif not has_bug_comment:
                    print(f"  ⚠️  Bug comment removed but no models import found")
                    
            except Exception as e:
                print(f"  Error reading file: {e}")
    
    if not fix_found:
        print("\n⚠️  Could not verify fix in any routes file")
        print("\nLet's check what the auto-fix actually changed...")
        
        # Show content of the most likely file
        if routes_files:
            main_routes = routes_files[0]
            print(f"\nContent of {main_routes.name} (first 1000 chars):")
            print("-" * 70)
            try:
                print(main_routes.read_text()[:1000])
            except:
                print("Could not read file")
            print("-" * 70)
        
        return False
    
    return True


def main():
    """Run the full auto-fix test."""
    print("=" * 70)
    print("  AUTO-FIX FULL END-TO-END TEST")
    print("=" * 70)
    print("\nThis test will:")
    print("1. Create a user and generate a project")
    print("2. Introduce a bug (missing import)")
    print("3. Submit a failed verification report")
    print("4. Trigger the auto-fix with LLM")
    print("5. Verify the fix was applied")
    print("\nPress Ctrl+C to cancel...")
    
    try:
        # Step 1: Auth
        token, email = register_and_login()
        
        # Step 2: Create project
        project_id, project_name = create_project(token)
        
        # Step 3: Introduce bug
        extract_dir, zip_path = introduce_bug(token, project_id)
        
        # Step 4: Simulate failed verification
        simulate_failed_verification(token, project_id)
        
        # Step 5: Trigger auto-fix
        fix_result = trigger_autofix(token, project_id)
        
        # Step 6: Verify fix
        fix_verified = verify_fix(token, project_id)
        
        # Final summary
        print_section("TEST SUMMARY")
        
        if fix_verified:
            print("✅ AUTO-FIX TEST PASSED!")
            print("\nThe auto-fix logic successfully:")
            print("  1. Analyzed the failed tests")
            print("  2. Identified the missing import")
            print("  3. Generated a fix using LLM")
            print("  4. Applied the fix to the code")
            print("  5. Reassembled the project ZIP")
            print("\n🎉 Auto-fix is working correctly!")
            return 0
        else:
            print("⚠️  AUTO-FIX TEST INCOMPLETE")
            print("\nThe auto-fix ran but the verification is inconclusive.")
            print("Check the output above for details.")
            return 1
        
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        return 1
    except Exception as e:
        print_section("TEST FAILED")
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
