# CraftLive — Agent Pipeline Flow

```mermaid
sequenceDiagram
    participant U as User (Chat UI)
    participant S as Supabase
    participant API as FastAPI
    participant IF as Interface Agent
    participant O as Orchestrator
    participant RAG as ChromaDB
    participant R as Requirements Agent
    participant A as Architecture Agent
    participant I as Implementer Agent
    participant TR as Test Runner
    participant TG as Test Generator Agent
    participant V as Reviewer Agent
    participant SB as Sandbox Executor
    participant LLM as OpenRouter API

    U->>S: Persist message
    U->>API: POST /generate/interface (prompt + context)
    API->>IF: Classify intent
    IF->>LLM: LLM call (MODEL_INTERFACE)
    LLM-->>IF: InterfaceDecision
    IF-->>API: InterfaceDecision

    alt Chat-only intent
        API-->>U: Direct assistant reply
    else Build intent
        API-->>U: Acknowledgment + trigger_pipeline=true
        U->>API: POST /generate/thread/{threadId}/chat (SSE)
        API->>O: Resolve thread→project, start pipeline

        O->>R: prompt + RAG context
        R->>LLM: System prompt + user prompt
        LLM-->>R: JSON (ProjectCharter)
        R-->>O: ProjectCharter (with graceful defaults if empty)
        O-->>U: SSE: requirements_done + Schema JSON

        O->>A: ProjectCharter
        A->>LLM: System prompt + charter
        LLM-->>A: JSON (SystemArchitecture + Mermaid)
        A-->>O: SystemArchitecture
        O-->>U: SSE: architecture_done

        O->>I: SystemArchitecture
        I->>LLM: Plan files then per-file code generation
        LLM-->>I: File contents
        I-->>O: GeneratedCode (files[])
        O-->>U: SSE: implementer_done

        O->>TR: GeneratedCode
        TR-->>O: TestReport (syntax + import checks)
        opt Deterministic failures found
            O->>I: Patch requests from TestRunner
            I->>LLM: Fix files
            LLM-->>I: Patched code
        end
        O-->>U: SSE: testing_done

        O->>TG: SystemArchitecture + GeneratedCode
        TG->>LLM: Generate pytest suite
        LLM-->>TG: GeneratedTests (test_files[])
        TG-->>O: GeneratedTests
        O-->>U: SSE: test_generation_done

        loop Review Loop (up to 5 passes, trust threshold ≥ 7)
            O->>V: GeneratedCode + previous score/issues
            V->>LLM: Review + fix pass
            LLM-->>V: ReviewReport
            alt Approved AND score ≥ 7
                V-->>O: Approved
            else Issues found or score < 7
                V-->>O: Issues + patch requests / rewritten code
                O->>I: Patch affected files
                I->>LLM: Fix files
                LLM-->>I: Patched code
            end
        end
        O-->>U: SSE: reviewer_done

        loop Sandbox Deploy (up to 3 attempts)
            O->>SB: Deploy code + tests to Docker container
            SB-->>O: SandboxTestReport
            alt Deployed + health OK + 0 test failures
                O-->>U: SSE: sandbox_deploy_done ✅
            else Failure
                O->>I: Patch requests from traceback parsing
                I->>LLM: Fix files
                LLM-->>I: Patched code
            end
        end

        O-->>U: SSE: completed
    end
```

## Artifact Types

| Stage | Pydantic Model | Key Fields |
|-------|---------------|------------|
| Requirements | `ProjectCharter` | project_name, entities, endpoints, business_rules, auth_required |
| Architecture | `SystemArchitecture` | design_document, mermaid_diagram, components, data_model_summary, endpoint_summary |
| Implementer | `GeneratedCode` | files (path + content), dependencies |
| Deterministic Tests | `TestReport` | passed, checks_run, failures, patch_requests |
| Test Generation | `GeneratedTests` | test_files (path + content), dependencies |
| Reviewer | `ReviewReport` | issues, suggestions, security_score, approved, final_code, patch_requests |
| Sandbox | `SandboxTestReport` | deployed, health_check_ok, tests_passed, tests_failed, tests_total, failures, test_output |

## SSE Event Stream

| Event | Stage | Payload |
|-------|-------|---------|
| `starting` | Init | message |
| `requirements` | Requirements | message |
| `requirements_done` | Requirements | artifact JSON |
| `architecture` | Architecture | message |
| `architecture_done` | Architecture | artifact JSON |
| `implementer` | Implementer | message |
| `implementer_done` | Implementer | files_count, artifact JSON |
| `testing` | Deterministic Tests | message |
| `testing_fix` | Deterministic Tests | failures, message |
| `testing_done` | Deterministic Tests | passed, checks |
| `test_generation` | Test Generation | message |
| `test_generation_done` | Test Generation | test_files |
| `reviewer` | Reviewer | attempt, prev_score, message |
| `revision` | Reviewer | attempt, score, issues_count |
| `reviewer_done` | Reviewer | score, artifact |
| `sandbox_deploy` | Sandbox | attempt, message |
| `sandbox_retry` | Sandbox | attempt, errors |
| `sandbox_deploy_done` | Sandbox | artifact (SandboxTestReport) |
| `completed` | Final | summary, all captured artifacts |
| `error` | Any | error message |
