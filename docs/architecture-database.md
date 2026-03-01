# CraftLive — Database Schema

## Backend Database (PostgreSQL via SQLModel)

```mermaid
erDiagram
    USER ||--o{ PROJECT : owns
    USER ||--o{ ITEM : owns
    PROJECT ||--o{ GENERATION_RUN : has
    PROJECT ||--o{ DOCUMENT : contains
    GENERATION_RUN ||--o{ ARTIFACT_RECORD : produces

    USER {
        uuid id PK
        string email UK
        string hashed_password
        string full_name
        bool is_active
        bool is_superuser
        datetime created_at
    }

    PROJECT {
        uuid id PK
        string name
        string description "stores [chat-thread:ID] marker"
        uuid owner_id FK
        datetime created_at
    }

    GENERATION_RUN {
        uuid id PK
        string status "pending|requirements|architecture|implementer|reviewer|completed|failed"
        string prompt "truncated at 5000 chars"
        uuid project_id FK
        datetime created_at
    }

    ARTIFACT_RECORD {
        uuid id PK
        string stage "requirements|architecture|implementer|deterministic_tests|test_generation|reviewer_pass_N|sandbox_tests_attempt_N"
        json content "Pydantic model dumped to dict; large code bundles stored via artifact_store"
        uuid run_id FK
        datetime created_at
    }

    DOCUMENT {
        uuid id PK
        string filename
        string content_type
        string project_id
        datetime created_at
    }

    ITEM {
        uuid id PK
        string title
        string description
        uuid owner_id FK
        datetime created_at
    }
```

## Frontend Database (Supabase)

```mermaid
erDiagram
    THREAD ||--o{ MESSAGE : contains
    MESSAGE ||--o{ MESSAGE_ATTACHMENT : has
    MESSAGE ||--o| MESSAGE_ARTIFACT : stores

    THREAD {
        uuid id PK
        string title
        uuid user_id FK
        datetime created_at
    }

    MESSAGE {
        uuid id PK
        uuid thread_id FK
        string role "user|assistant|agent"
        text content
        json metadata "generatedFileMap, runMode, etc."
        datetime created_at
    }

    MESSAGE_ATTACHMENT {
        uuid id PK
        uuid thread_id FK
        uuid message_id FK
        uuid user_id FK
        string original_name
        string mime_type
        int size_bytes
        datetime created_at
    }

    MESSAGE_ARTIFACT {
        uuid id PK
        uuid message_id FK
        json payload "requirementsArtifact, architectureArtifact, generatedFileMap"
        datetime created_at
    }
```

## Thread ↔ Project Mapping

The frontend uses Supabase threads; the backend uses PostgreSQL projects. They are linked via:

```
Project.description = "[chat-thread:{supabase_thread_id}]"
```

This marker is set by `_resolve_or_create_project_for_thread()` in `generate.py` and queried by:
- `generate.py` — to reuse the same project across multiple runs in one thread
- `sandbox.py` — to locate the project when deploying by thread ID

## Artifact Storage

Large generated code bundles are stored on disk via `artifact_store.py` rather than being inlined into the database JSON. The `ArtifactRecord.content` field contains a `bundle_ref` path pointing to the file on disk in `backend/artifact_store/`.

## Transaction Safety

All CRUD operations (`create_user`, `create_project`, `create_generation_run`, `create_artifact_record`) are wrapped in:

```python
try:
    session.add(obj)
    session.commit()
    session.refresh(obj)
except Exception:
    session.rollback()
    raise
```
