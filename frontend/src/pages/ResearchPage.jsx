import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

export const RESEARCH_POSTS = [
    {
        id: "architecture-of-agentic-ai",
        title: "The Architecture of Agentic AI: Beyond Simple Prompting",
        excerpt: "An exploration into proactive, goal-driven Agentic AI systems capable of autonomous tool-use and deep reasoning.",
        author: "Nicole N. Nanka-Bruce",
        date: "Feb 10, 2026",
        category: "Agentic AI",
        readTime: "8 min read",
        bgConfig: "linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%)", // Very subtle grey
        textColor: "var(--text-primary)",
        content: `INTRODUCTION

The architectural evolution of Large Language Models (LLMs) has transitioned rapidly from stateless, reactive text generation to stateful, goal-oriented "Agentic" systems. This paper explores the theoretical underpinnings and practical implementations of autonomous tool-use frameworks.

THE STATE OF REACTIVE GENERATION
Historically, LLMs have behaved as pure functions: mapping an input prompt to an output sequence. While highly effective for zero-shot tasks, this paradigm fails when confronting complex, multi-step engineering problems that require trial, error, and memory.

ENTER THE AGENT
We define an "Agent" not merely as a model, but as a composite system comprising a core reasoning engine (the LLM), memory (short-term context and long-term vector stores), and tools (APIs, REPLs, browsers). 

By implementing frameworks such as ReAct (Reasoning and Acting) and Reflection, early experiments show a 40% reduction in hallucination rates during complex software synthesis. The agent is forced to justify its actions in a "scratchpad" before execution, allowing it to evaluate its own trajectory and course-correct when a tool returns an error.

FUTURE DIRECTIONS
As context windows expand beyond 1M tokens, the necessity for explicit reasoning steps becomes paramount. Our findings suggest that future development should focus less on raw parameter count, and more on the systemic orchestration of smaller, specialized models operating in tandem.`
    },
    {
        id: "post-training-llms",
        title: "Advancements in Post-Training LLMs: RLHF, DPO, and Beyond",
        excerpt: "A review of modern alignment techniques, assessing their impact on model safety and steerability.",
        author: "Elijah K. A. Boateng",
        date: "Feb 05, 2026",
        category: "Post Training LLMs",
        readTime: "12 min read",
        bgConfig: "linear-gradient(135deg, rgba(255, 236, 210, 0.5) 0%, rgba(252, 182, 159, 0.2) 100%)", // Very subtle warm
        textColor: "var(--text-primary)",
        content: `ABSTRACT

Modern foundation models achieve baseline coherence through pre-training, but their specific utility and safety profiles are defined during the post-training alignment phase. This study provides a comparative analysis of Reinforcement Learning from Human Feedback (RLHF) and the more recent Direct Preference Optimization (DPO).

THE RLHF BOTTLENECK
Traditional alignment via RLHF involves training a separate reward model based on human preference data, which is then used to optimize the policy model via Proximal Policy Optimization (PPO). While highly effective, this pipeline is notoriously unstable, sensitive to hyperparameters, and computationally expensive.

THE DPO PARADIGM SHIFT
Direct Preference Optimization simplifies this by treating the reward modeling and policy optimization as a single, combined objective. By implicitly defining the reward via the LLM policy itself, DPO completely sidesteps the need for a standalone reward model or complex PPO loops.

EMPIRICAL FINDINGS
Our internal benchmarks across three coding-centric evaluation suites reveal that DPO-aligned models converge 3x faster than their RLHF counterparts with equivalent computational budgets. Furthermore, DPO exhibits significantly lower variance across runs, resulting in more predictable alignment behaviors. However, we note that DPO can occasionally over-optimize for stylistic verbosity rather than structural accuracy.`
    },
    {
        id: "multiagent-systems",
        title: "Multiagent Systems: Cooperative Problem Solving",
        excerpt: "Analyzing the emergent behaviors of decentralized multiagent protocols for complex engineering tasks.",
        author: "Joseph A. Ajegetina",
        date: "Jan 28, 2026",
        category: "Multiagent Systems",
        readTime: "15 min read",
        bgConfig: "linear-gradient(135deg, rgba(224, 195, 252, 0.3) 0%, rgba(142, 197, 252, 0.2) 100%)", // Very subtle cool
        textColor: "var(--text-primary)",
        content: `INTRODUCTION

As single-agent systems approach their theoretical limitations in complex software orchestration, decentralized multiagent protocols offer a robust alternative. This paper analyzes emergent problem-solving behaviors when specialized agents act cooperatively within a shared, N-dimensional state space.

TOPOLOGY OF AGENT NETWORKS
We propose a hierarchical topology consisting of a "Director" agent and several subordinate "Worker" agents (e.g., Coder, Reviewer, Tester). Theoretical analysis proves that partitioning context among specialized agents reduces the overall perplexity of the system compared to a monolithic agent attempting to maintain global state.

SHARED STATE MECHANISMS
The critical bottleneck in multiagent systems is information relay. We introduce a distributed "Blackboard" architecture—a shared, stateful data structure that all agents can read from and write to concurrently. This allows asynchronous problem-solving where, for example, the Tester agent can immediately flag anomalous output while the Coder agent is still generating subsequent logic.

RESULTS
Deploying this architecture on the exhaustive SWE-bench dataset yielded a 22% increase in absolute resolution rate compared to state-of-the-art single-agent reasoners.`
    },
    {
        id: "retrieval-augmented-generation",
        title: "Retrieval-Augmented Generation (RAG): Optimizing Vector Search",
        excerpt: "Investigating advanced indexing mechanisms and chunking strategies to enhance enterprise RAG pipelines.",
        author: "Innocent F. Chikwanda",
        date: "Jan 15, 2026",
        category: "RAG",
        readTime: "10 min read",
        bgConfig: "linear-gradient(135deg, rgba(212, 252, 121, 0.3) 0%, rgba(150, 230, 161, 0.2) 100%)", // Very subtle green
        textColor: "var(--text-primary)",
        content: `THE LIMITATIONS OF PARAMETRIC MEMORY

Language models, regardless of size, suffer from static parametric memory. They cannot access proprietary, real-time, or heavily localized data without fine-tuning. Retrieval-Augmented Generation (RAG) circumvents this by fetching relevant data at inference time and injecting it into the context window.

OPTIMIZING VECTOR SEARCH
Standard dense retrieval using cosine similarity on sentence embeddings often fails in codebases due to structural lexical dependencies. We propose a hybrid "Lexical-Semantic" approach. By combining keyword-based BM25 scoring with dense vector search, retrieval recall in complex repositories improves by 34%.

ADVANCED CHUNKING STRATEGIES
Naïve text splitting truncates necessary context. For software engineering, we introduce Abstract Syntax Tree (AST)-aware chunking. By preserving function and class boundaries during the embedding process, the retrieval mechanism returns logical, self-contained units of code rather than fragmented strings.

CONCLUSION
As context windows grow to 1M+ tokens, the role of RAG shifts from a necessity for memory to a necessity for precision and cost-reduction. Efficient retrieval remains the most viable method for interacting with massive enterprise repositories.`
    },
    {
        id: "rigorous-evaluation-metrics",
        title: "Rigorous Evaluation Metrics for Autonomous LLM Agents",
        excerpt: "Proposing a novel, multi-dimensional evaluation methodology focusing on trajectory robustness and tool utility.",
        author: "Nicole N. Nanka-Bruce",
        date: "Jan 08, 2026",
        category: "Evaluation of Agents",
        readTime: "11 min read",
        bgConfig: "linear-gradient(135deg, rgba(251, 194, 235, 0.3) 0%, rgba(166, 193, 238, 0.2) 100%)", // Very subtle pink/blue
        textColor: "var(--text-primary)",
        content: `THE BENCHMARK CRISIS

Current evaluations for Large Language Models (like MMLU or HumanEval) primarily test zero-shot generation or static factual recall. However, these benchmarks fail completely to capture the dynamic, non-deterministic realities of deploying autonomous agents in the wild.

PROPOSING A NEW METHODOLOGY: TRAJECTORY EVALUATION
We introduce a framework that shifts evaluation from "Did the model produce the right string?" to "Did the model take the right actions?". This involves tracking the agent's trajectory through an environment.

KEY METRICS
1. Tool Utility Rate: The ratio of successful tool invocations to total tool invocations. High tool failure indicates poor formatting adherence or reasoning flaws.
2. Context Bleed: Measuring how often an agent "forgets" parameters defined earlier in the interaction loop.
3. Path Efficiency: The number of actions taken to resolve a task compared to the optimal human baseline.

IMPLEMENTATION
By deploying agents in isolated, reproducible Docker containers with mocked APIs, we can reliably stress-test their ability to recover from unexpected errors, providing a much stronger signal of operational readiness than traditional static tests.`
    },
    {
        id: "intelligent-orchestration",
        title: "Intelligent Orchestration: Synchronizing Stateful Microservices",
        excerpt: "Systemic design patterns to bridge natural language understanding with deterministic API routing.",
        author: "Elijah K. A. Boateng",
        date: "Dec 19, 2025",
        category: "Orchestration",
        readTime: "9 min read",
        bgConfig: "linear-gradient(135deg, rgba(207, 217, 223, 0.4) 0%, rgba(226, 235, 240, 0.3) 100%)", // Subtle steel
        textColor: "var(--text-primary)",
        content: `INTRODUCTION

The integration of non-deterministic Large Language Models into strict, deterministic microservice architectures presents a significant systemic risk. This paper details design patterns for utilizing LLMs as intelligent directors without compromising system reliability.

THE ORCHESTRATOR PATTERN
We define an architecture where the LLM does not execute code directly, but rather emits structured intents (e.g., JSON schemas) that are parsed and validated by a deterministic routing layer. This "Air Gap" ensures that hallucinated parameters or malformed syntax cannot bring down core infrastructure.

STATE SYNCHRONIZATION
When an LLM director orchestrates multiple microservices (e.g., initiating a payment, reserving inventory, dispatching an email), it must maintain transaction integrity. We introduce an LLM-compatible "Saga Pattern" mechanism. If a downstream service fails, the deterministic router feeds the error state back to the LLM, triggering a pre-defined compensation sequence (e.g., issuing a refund).

CONCLUSION
Treating the LLM not as a traditional software component, but as an unpredictable user interacting with a strict API, is the safest methodology for enterprise orchestration. By enforcing strict schema validation at the boundary layer, we can harness the dynamic reasoning capabilities of post-training models while maintaining zero-trust reliability.`
    }
];

export default function ResearchPage({ onOpenLogin, theme, onThemeToggle }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--bg-primary)' }}>
            <Navbar onLoginClick={onOpenLogin} theme={theme} onThemeToggle={onThemeToggle} />

            <main style={{ flex: 1, padding: '120px 20px', maxWidth: '1400px', margin: '0 auto', width: '100%' }}>
                <header style={{ textAlign: 'center', marginBottom: '80px' }}>
                    <h1 style={{ fontSize: 'clamp(2.5rem, 5vw, 4rem)', fontWeight: '700', letterSpacing: '-0.03em', marginBottom: '20px' }}>
                        Our Research
                    </h1>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem', maxWidth: '600px', margin: '0 auto' }}>
                        Scientific discourse, technical deep dives, and academic perspectives on the frontiers of artificial intelligence and distributed systems.
                    </p>
                </header>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '30px' }}>
                    {RESEARCH_POSTS.map(post => (
                        <Link to={`/research/${post.id}`} key={post.id} style={{ textDecoration: 'none' }}>
                            <article style={{
                                background: post.bgConfig,
                                aspectRatio: '1',
                                borderRadius: '12px',
                                padding: '36px',
                                display: 'flex',
                                flexDirection: 'column',
                                justifyContent: 'flex-start',
                                transition: 'opacity 0.2s ease',
                                cursor: 'pointer',
                                color: post.textColor,
                                position: 'relative',
                                overflow: 'hidden'
                            }}
                                onMouseEnter={e => e.currentTarget.style.opacity = '0.9'}
                                onMouseLeave={e => e.currentTarget.style.opacity = '1'}
                            >
                                <div style={{ flex: 1 }}>
                                    <div style={{ fontSize: '0.8rem', fontWeight: '500', color: 'var(--text-secondary)', letterSpacing: '0.02em', textTransform: 'uppercase', marginBottom: '16px' }}>
                                        {post.category} • {post.date}
                                    </div>
                                    <h2 style={{ fontSize: '1.35rem', lineHeight: '1.4', fontWeight: '600', letterSpacing: '-0.01em', marginBottom: '16px' }}>
                                        {post.title}
                                    </h2>
                                    <p style={{ fontSize: '0.95rem', lineHeight: '1.5', color: 'var(--text-secondary)', opacity: 0.9 }}>
                                        {post.excerpt.length > 120 ? post.excerpt.substring(0, 120) + '...' : post.excerpt}
                                    </p>
                                </div>
                                <div style={{ fontSize: '0.95rem', fontWeight: '500', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)' }}>
                                    <div style={{ width: 24, height: 24, borderRadius: '50%', background: 'var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px' }}>
                                        {post.author.charAt(0)}
                                    </div>
                                    {post.author}
                                </div>
                            </article>
                        </Link>
                    ))}
                </div>
            </main>

            <Footer />
        </div>
    );
}
