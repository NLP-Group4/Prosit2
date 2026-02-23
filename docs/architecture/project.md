We are designing a fully functional backend generation platform.

This will be:

> A production-grade MVP blueprint
> Compatible with Google Agent SDK
> Deterministic
> Incrementally extensible

Follow the spec below

---

# BACKEND GENERATION PLATFORM — MVP EXECUTION SPEC

---

# 1. System Objective

Build a web platform that:

1. Accepts a natural language prompt
2. Converts it into a structured backend specification
3. Validates the specification
4. Generates a deterministic FastAPI backend
5. Packages it as a Dockerized deployable artifact
6. Exposes OpenAPI/Swagger automatically

Scope is intentionally constrained.

---

# 2. Non-Goals (Hard Constraints)

The MVP MUST NOT include:

* Multiple backend frameworks
* GraphQL
* Background jobs
* Event systems
* Microservices
* Multi-database support
* UI builder
* Auto cloud deployment
* Live multi-tenant runtime

This is a single-project code generator.

---

# 3. Canonical Stack (Fixed)

Stack is locked for MVP:

* Python 3.11
* FastAPI
* PostgreSQL
* SQLAlchemy
* Alembic (optional but recommended)
* JWT authentication
* Docker
* Pydantic v2

No flexibility.

---

# 4. High-Level Architecture

```
Frontend (Prompt Input UI)
        ↓
Backend Builder API (FastAPI)
        ↓
Agent Orchestrator (Google Agent SDK)
        ↓
Spec Agent
        ↓
Spec Validator
        ↓
Code Generation Agent
        ↓
Project Assembler
        ↓
Artifact Store (Zip)
```

---

# 5. Google Agent SDK Architecture

You will implement 3 agents.

Keep this simple.

---

## Agent 1: PromptToSpecAgent

### Responsibility

Convert user prompt → strict JSON backend specification.

### Output Requirements

* Must return valid JSON only.
* Must conform exactly to the Spec Schema.
* No explanations.
* No comments.
* No markdown.

### Failure Handling

* If schema invalid → automatic retry up to 2 times.
* If still invalid → fail with structured error.

---

## Agent 2: SpecReviewAgent

### Responsibility

* Validate logical consistency.
* Detect:

  * Duplicate entity names
  * Missing primary keys
  * Invalid field types
  * Circular relationships (future)
* Normalize casing.

This agent does NOT modify architecture.
It only validates and rejects.

---

## Agent 3: CodeGenerationAgent

### Responsibility

Consumes validated spec and outputs:

* Folder structure definition
* File contents (per file)
* Requirements file
* Dockerfile

This agent must NOT improvise structure.
It must use predefined templates.

---

# 6. Canonical Backend Specification Schema

This is the most critical artifact.

This is your Intermediate Representation (IR).

```json
{
  "project_name": "string",
  "description": "string",
  "database": {
    "type": "postgres",
    "version": "15"
  },
  "auth": {
    "enabled": true,
    "type": "jwt",
    "access_token_expiry_minutes": 30
  },
  "entities": [
    {
      "name": "User",
      "table_name": "users",
      "fields": [
        {
          "name": "id",
          "type": "uuid",
          "primary_key": true,
          "nullable": false,
          "unique": true
        },
        {
          "name": "email",
          "type": "string",
          "nullable": false,
          "unique": true
        }
      ],
      "crud": true
    }
  ]
}
```

---

# 7. Allowed Field Types

Strict whitelist:

* string
* integer
* float
* boolean
* datetime
* uuid
* text

Anything else → reject.

---

# 8. Deterministic Project Structure

Code generation MUST output exactly this structure:

```
project_name/
│
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── crud.py
│   ├── auth.py
│   ├── config.py
│   └── routers/
│        └── <entity>.py
│
├── alembic/
│
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

No variation allowed.

---

# 9. Code Generation Rules

The CodeGenerationAgent must obey:

1. Use SQLAlchemy ORM (declarative)
2. UUID primary keys defaulted
3. Dependency injection for DB session
4. Separate Pydantic schemas:

   * Base
   * Create
   * Update
   * Response
5. All CRUD endpoints auto-generated if `crud: true`
6. All endpoints tagged per entity
7. JWT auth middleware if enabled

---

# 10. Generated Endpoints Pattern

If entity = Product

Auto-generate:

```
POST   /products
GET    /products
GET    /products/{id}
PUT    /products/{id}
DELETE /products/{id}
```

If auth enabled:

* Protected by JWT dependency

---

# 11. Progressive Development Phases

You will build this system incrementally.

---

## Phase 1 — Manual Spec → Code Generator

Goal:

* Skip prompt agent.
* Manually feed JSON spec.
* Generate working backend.

This validates:

* Templates
* Folder structure
* Docker build

Do this FIRST.

---

## Phase 2 — Add PromptToSpecAgent

Now:

* Accept prompt
* Generate spec
* Validate
* Pass to generator

---

## Phase 3 — Add Validation Agent

Add logical guardrails before code generation.

---

## Phase 4 — Add UI Layer

Basic web UI:

* Text input
* “Generate Backend” button
* Download ZIP

Nothing more.

---

# 12. Google Agent SDK Orchestration Flow

Pseudo-logic:

```
spec = PromptToSpecAgent.run(prompt)

validated_spec = SpecReviewAgent.run(spec)

project_files = CodeGenerationAgent.run(validated_spec)

assemble_project(project_files)

zip_project()

return download_link
```

Each step must be atomic.

No shared mutation.

---

# 13. Determinism Strategy

To reduce LLM variance:

1. Always provide schema in prompt
2. Force JSON response
3. Use temperature ≤ 0.2
4. Validate with Pydantic
5. Retry invalid output

---

# 14. Security Defaults

Always include:

* CORS middleware
* Environment-based config
* SECRET_KEY required
* Hashed passwords (bcrypt)
* No plain password storage

---

# 15. Minimal Prompt Template for Spec Agent

Use strict instruction:

"You are generating a backend specification.
Return ONLY valid JSON matching the schema below.
Do not include markdown.
Do not include commentary."

Include full schema in prompt.

---

# 16. Testing Strategy

For MVP:

1. Unit test generator using:

   * 1 entity
   * 2 entities
   * Auth on/off
2. Docker build test
3. Run `uvicorn`
4. Confirm `/docs` works
5. Confirm CRUD works

---

# 17. Versioning

Include:

```
"spec_version": "1.0"
```

This prevents future breakage.

---

# 18. Deliverables Checklist

Your MVP is complete when:

* Prompt → backend zip works
* Docker runs without modification
* Swagger UI loads
* CRUD works
* JWT works
* Database connects

Nothing else matters.

---

# 19. Future Extensions (Not Now)

* Relationships
* RBAC
* Soft deletes
* Pagination
* Filtering
* Background tasks
* Redis
* Multi-env deployment

---

# 20. Final Engineering Principle

This system must behave like:

> A deterministic backend compiler
> Not a creative coding assistant

Everything passes through the Spec IR.

