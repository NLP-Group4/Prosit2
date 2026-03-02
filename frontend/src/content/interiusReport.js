export const INTERIUS_REPORT_AUTHORS = [
    'Nicole N. Nanka-Bruce',
    'Joseph A. Ajegetina',
    'Innocent F. Chikwanda',
    'Elijah K. A. Boateng'
];

export const INTERIUS_REPORT_CONTENT = `
## Abstract

**Interius** is an autonomous backend engineering system that transforms natural-language intent into a reviewed, structured, and testable backend application. Rather than relying on one-shot code generation, the system decomposes software creation into a staged pipeline consisting of requirements synthesis, architecture design, implementation, review, repair, and runtime validation. This report presents the motivation for the system, the architecture that supports it, the security and runtime design choices that shape it, and the evaluation framework used to study its behavior. The central claim is that backend generation becomes substantially more reliable when it is treated as a systems problem rather than a single prompt-response interaction. Interius therefore combines agent specialization, artifact persistence, retrieval-augmented reasoning, and runtime verification into one end-to-end workflow.

## 1. Introduction

The practical challenge that motivates Interius is straightforward. Building a backend remains difficult even when the desired product behavior is already clear. Non-technical builders often understand the product they want but cannot express it in terms of models, routes, authentication rules, validation logic, or deployment steps. Developers, by contrast, may understand all of those concepts but still spend a disproportionate amount of time on repetitive scaffolding, debugging, coordination across files, and recovery from small architectural inconsistencies. Existing large language model workflows reduce some of the manual burden, but they tend to degrade as soon as the requested system becomes multi-file, stateful, security-sensitive, or architecturally non-trivial.

Interius was designed in response to that gap. The system assumes that backend generation is not one problem but several tightly coupled problems. Before code can be produced, the request must be interpreted. Before implementation can be trusted, structure must be planned. Before the result can be released, it must be reviewed and then exercised in a runtime environment. The product is therefore built around the idea that software generation should follow the same disciplined progression that human teams use: first clarify the problem, then define the system, then implement it, then inspect it, then test it.

## 2. Problem Setting

Traditional single-pass LLM generation is often impressive at the level of snippets and small examples, yet unreliable for full backend systems. The failure is rarely due to syntax alone. More commonly, the model loses coherence across multiple files, drifts away from the original specification, introduces inconsistent naming or data contracts, or produces code that appears plausible but fails during startup. Security is another source of fragility. Authentication flows, token handling, archive generation, and request validation all create opportunities for subtle defects that are easy for a generative model to miss when it is asked to plan and implement an entire application in one step.

The design hypothesis behind Interius is therefore that multi-file backend generation must be explicitly structured. If the system can preserve intermediate artifacts, separate roles across specialized agents, and validate results against both deterministic checks and runtime behavior, then the resulting applications should be more coherent and easier to recover when failures occur.

## 3. Terminology

Several terms recur throughout this report. An **agent** is a specialized model-driven component with a narrow responsibility, such as producing requirements or reviewing code. A **pipeline** is the ordered sequence of stages that carries a prompt from intent to final artifact. An **artifact** is any structured output produced by one of those stages, including requirements documents, architectural plans, and code bundles. **Server-Sent Events (SSE)** are the streaming messages used to report pipeline progress to the frontend in real time. **Retrieval-Augmented Generation (RAG)** refers to the use of retrieved context during answering or generation, typically through stored text chunks and semantic search. **Embeddings** are vector representations of text that allow semantic similarity search over those chunks. **ChromaDB** is the vector store used by Interius for document and generated-code retrieval. **OpenAPI** is the schema format used to describe the generated API, and **Swagger UI** is the browser-based interface that uses that schema for live interactive testing. The **sandbox** is the isolated runtime where generated code is deployed for validation before it is shown to the user. A **JWT**, or JSON Web Token, is a signed token commonly used in stateless authentication. Terms such as **prompt injection**, **mass assignment**, **path traversal**, and **ZIP bomb** refer to classes of attacks or unsafe behaviors that the security layer is designed to detect or prevent. Finally, **autofix** refers to the repair loop that patches generated code after review or runtime failure.

## 4. System Overview

At a high level, Interius accepts a user request for a backend and routes it through a control layer that determines whether the request should be answered conversationally, answered using previously generated code context, or sent into the generation pipeline. When a full generation run is triggered, the system creates a chain of structured stages that produce requirements, architecture, implementation, review findings, and repaired code artifacts. These outputs are streamed to the frontend as the run progresses, stored for later inspection, and, when appropriate, indexed for follow-up explanation.

The system is deliberately multi-interface. In the browser, the user can inspect requirements and architecture artifacts, preview generated code, open a live sandbox, and test the generated API through Swagger UI or an API tester panel. In the CLI, the same backend intelligence is retained, but the final code is written into the user’s local project and the generated FastAPI application is launched locally. This separation between reasoning and execution is one of the project’s key design choices.

## 5. Architecture

![Full Interius architecture.](/research/interius/full-architecture.png)

The architecture is divided into a frontend layer, a backend orchestration layer, specialized agents, storage systems, and model providers. The frontend is responsible for presenting streamed progress, collected artifacts, uploaded documents, and runtime testing surfaces. The backend acts as the control plane: it receives prompts, persists generation runs, coordinates agent execution, stores artifacts, manages sandbox deployment, and proxies runtime interactions.

An interface agent sits at the front of the backend workflow. Its purpose is to prevent unnecessary full pipeline runs by distinguishing between ordinary chat, generated-code question answering, and actual build intent. Once build intent is recognized, control is handed to an orchestrator that executes the specialized generation stages. The orchestrator does not simply forward prompts. Instead, it manages artifact boundaries and stage ordering, allowing later stages to consume structured outputs from earlier ones.

The surrounding storage and service layer supports this orchestration. PostgreSQL provides durable backend persistence. Supabase is used on the frontend side for thread and message continuity. ChromaDB stores both uploaded document chunks and generated-code chunks so that Interius can later answer grounded questions about prior outputs. External model providers, including OpenAI, Groq, and Gemini embeddings, support different parts of the reasoning and retrieval stack.

## 6. Multi-Agent Pipeline

The generation pipeline begins with the Requirements Agent, whose role is to convert informal user intent into a structured specification. This artifact describes the target application in product and engineering terms rather than immediately producing code. It typically captures the project name, domain entities, endpoint expectations, constraints, and assumptions. This stage matters because poor requirements propagate downstream as architectural ambiguity and code drift.

The Architecture Agent then converts that requirements artifact into a software blueprint. This includes decisions about model relationships, route organization, authentication placement, and general package structure. The purpose of this stage is not cosmetic. In practice, many code-generation failures happen because models are able to produce convincing files but not convincing systems. Introducing architecture as its own artifact addresses that problem directly.

Implementation is handled by the Implementer Agent. Unlike monolithic code generation, this agent works in a file-oriented manner so that affected files can later be regenerated without rewriting the entire project. That design is important for iterative correction. When review or repair identifies a localized failure, the system can issue focused patch requests instead of discarding the full code bundle.

The Reviewer Agent performs the first major quality gate over the generated code. In the current design it focuses on structured review and deterministic validation rather than live runtime deployment. It checks whether the code remains faithful to the prior requirements and architecture, whether dangerous or unsupported patterns appear, and whether the generated structure is internally coherent. If problems are found, the reviewer emits file-level patch requests that are sent back to the implementer for targeted revision.

The final stage in the web-oriented path is the Repair Agent. This stage turns runtime behavior into a first-class signal. Generated code is deployed into a sandbox, logs are collected, OpenAPI is inspected, and endpoint smoke checks are performed. If runtime failures occur, the repair process sends targeted instructions back through the implementation path and retries. In the CLI-oriented path, the backend can skip Docker-backed sandbox repair and delegate execution to the CLI, which writes files locally and starts the application in the user’s environment.

## 7. Retrieval-Augmented Components

Interius uses retrieval for two distinct but related purposes. The first is document retrieval. Uploaded files are parsed, segmented into chunks, embedded, and stored in ChromaDB so that relevant context can be retrieved later. The second is generated-code retrieval. After a successful run, generated files are chunked and indexed on a per-thread basis. This allows users to ask grounded follow-up questions such as where authentication is implemented or how a specific route works.

This distinction is important. Document retrieval helps the system reason over external source material. Generated-code retrieval helps the system explain its own outputs after generation. Together, these features move Interius beyond blind code generation and toward inspectable system behavior.

## 8. Security Design

![Security architecture for Interius.](/research/interius/security-architecture.png)

Security in Interius is not treated as a single post hoc scan. It is layered across the lifecycle of the request. At the input level, the system validates structured specifications and checks for prompt manipulation patterns, including prompt injection and crescendo-style multi-step escalation. At the code level, generated files are inspected for dangerous or unsupported patterns that could cause either security weaknesses or unstable runtime behavior. At runtime, the system checks concerns such as authentication enforcement, JWT verification and tampering resistance, SQL injection risk, and mass assignment exposure. Finally, because generated artifacts may be downloaded as archives, archive safety checks are also applied to defend against ZIP bombs, symlink abuse, and path traversal.

The value of this layered design is that no single gate is treated as sufficient. A generation that appears structurally plausible may still be insecure. A runtime that starts cleanly may still expose an unsafe archive or weak authentication flow. By distributing security checks across stages, Interius reduces the likelihood that a failure in one layer remains invisible to the system as a whole.

## 9. Interfaces and Distribution

Interius is built for both hosted and local use. The web application serves as the primary interactive interface, with support for streamed generation, artifact inspection, schema visualization, sandbox deployment, and live API testing. This makes the browser suitable for demonstration, collaborative inspection, and human-in-the-loop review.

The CLI introduces a more developer-oriented distribution model. Users install the CLI package, authenticate it against a reachable Interius backend, and invoke the system from within a local project directory. The backend remains the reasoning engine, while the CLI becomes the local execution arm. It gathers workspace context, receives the final code bundle, writes files into the local folder, creates or reuses a Python virtual environment, installs dependencies, starts the generated FastAPI service, and prints the local Swagger UI link. In effect, the CLI allows Interius to function as a local software agent without moving model orchestration out of the backend.

## 10. Runtime Validation and Sandbox Strategy

The sandbox exists to answer a practical question that static code review cannot answer: does the generated application actually start and expose a usable API? In the web pipeline, generated files are written into an isolated directory, dependencies are resolved, the application is launched with Uvicorn, and the system waits for the service to become reachable. It then inspects the resulting OpenAPI schema and exercises selected endpoints. If startup fails or the API appears to fall back to an incomplete shell application, those failures become repair inputs.

This strategy makes the pipeline stronger than syntax-based validation alone, but it should not be overstated. A sandbox that boots successfully and serves endpoints has passed an important threshold, but not a final one. Correctness at scale, production configuration, domain fidelity, and long-tail behaviors all remain separate concerns. The runtime gate is therefore best understood as a high-value prototype validation layer rather than a proof of production readiness.

## 11. Evaluation

Interius is evaluated across quality, security, and repair dimensions because backend generation cannot be summarized responsibly by a single number. A system may parse structured specifications correctly yet fail runtime checks. It may start successfully but violate authentication expectations. It may look coherent to a judge model while still containing endpoint or schema errors. The evaluation framework is therefore explicitly multi-metric.

The quality profile of the current system is strong. Spec Parse Rate, Field Type Accuracy, Convention Compliance, and Entity Completeness are all reported at 100.0%, suggesting that the structured generation stages are highly consistent. Auth Faithfulness is reported at 95.0%, First Attempt Success Rate at 85.0%, Pipeline End-to-End Pass Rate at 90.0%, and HTTP Verification Pass Rate at 95.0%. Together, these values indicate that the most reliable part of the system is its structured planning and assembly, while the remaining variability comes from first-pass runtime convergence and security-sensitive implementation details.

The security evaluation is similarly encouraging. Cross Model Auth Agreement, Injection Resistance Rate, Crescendo Robustness, Code Safety Clean Rate, Auth Enforcement Rate, JWT Tampering Rejection Rate, and ZIP Safety Clean Rate are all reported at 100.0%, with Auth Faithfulness at 95.0%. These results suggest that the security architecture is not merely diagrammatic; it corresponds to explicit measurement and checking. At the same time, those results should be interpreted as evidence of strong prototype behavior rather than a universal guarantee across arbitrary prompts and domains.

Repair-oriented evaluation is especially important because one of Interius’s research claims is that generation quality depends not only on initial output quality but also on the system’s capacity to recover. The reported Autofix Success Rate is 80.0%, with an Autofix Mean Attempts value of 1.25 and an Autofix Validation Pass Rate of 100.0%. Cross Model Entity Variance is reported at 0.33, Cross Model Field Consistency at 100.0%, Cross Model Structural Similarity at 0.96, and an LLM Judge Completeness Score at 76.0%. These numbers imply that repair is frequently effective and usually efficient, though not universal. Some cases still resist bounded repair loops.

The broader judge-based summary reports a Faithfulness Score of 83.3%, a Coherence Score of 100.0%, an Overall Score of 86.4%, and a Correctness Score of 86.4%. These metrics are useful as qualitative complements to deterministic validation, especially when interpreting whether a generated system appears complete and logically consistent. They should not, however, replace concrete runtime and structural checks.

## 12. Discussion

The strongest contribution of Interius is architectural rather than merely presentational. The system demonstrates that backend generation becomes more tractable when responsibilities are separated across agents and when outputs are treated as persistent, inspectable artifacts. This creates several benefits simultaneously. It improves traceability because each stage leaves behind a visible product. It improves repairability because later stages can target only the files implicated by a failure. It improves interpretability because users are able to inspect requirements, architecture, code, and runtime behavior separately. Most importantly, it creates natural insertion points for validation and security checks that would be difficult to apply coherently in a one-shot generation flow.

At the same time, Interius remains a prototype research system rather than a completed production platform. Sandbox success is a strong signal, but not a full guarantee of correctness. Bounded repair loops can still fail on more complex runtime defects. Multi-user ownership and isolation need stronger production hardening. Some remaining interface paths still reflect prototype-stage bridging decisions. These are not contradictions of the system design; they are the engineering constraints that define the next phase of work.

## 13. Conclusion

Interius should be understood as an autonomous backend engineering workflow rather than a plain code generator. It combines agent specialization, artifact persistence, retrieval, structured review, runtime validation, and dual-interface delivery into a single product system. The reported evaluation results suggest that this architecture already provides meaningful gains in reliability, coherence, and recoverability. The research implication is clear: backend generation is better approached as staged systems engineering than as direct text completion. The practical implication is equally clear: if the remaining work on isolation, scaling, and richer runtime recovery is completed, Interius can mature from a strong prototype into a robust software generation platform.
`;
