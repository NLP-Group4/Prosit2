"""
IntentRouter — Classifies the user's intent to decide:
  - RETRIEVE: Return the existing project (no new generation needed)
  - GENERATE: Start a new or updated generation pipeline
  - REFINE:   Tweak an existing spec based on thread history

Uses lightweight heuristics first (fast, free), then falls back to an LLM
for ambiguous cases.
"""

from __future__ import annotations

import re
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    RETRIEVE = "retrieve"   # User wants to access their existing project
    GENERATE = "generate"   # User wants a brand-new backend built
    REFINE   = "refine"     # User wants modifications to an existing project


# ---------------------------------------------------------------------------
# Heuristic patterns (fast, zero-cost)
# ---------------------------------------------------------------------------

_RETRIEVE_PATTERNS = re.compile(
    r"\b("
    r"where\s+is|give\s+me|send\s+me|show\s+me|get\s+me|download|"
    r"my\s+project|my\s+api|my\s+app|my\s+backend|"
    r"i\s+already|you\s+built|you\s+made|we\s+built|we\s+made|"
    r"link\s+to|zip|artifact|re-?download|resend"
    r")\b",
    re.IGNORECASE,
)

_GENERATE_PATTERNS = re.compile(
    r"\b("
    r"build|create|generate|make|scaffold|set\s+up|implement|write|"
    r"new\s+(api|backend|project|app|service)"
    r")\b",
    re.IGNORECASE,
)

_REFINE_PATTERNS = re.compile(
    r"\b("
    r"add|remove|update|change|fix|modify|extend|rename|"
    r"also|additionally|now\s+also|i\s+also\s+want|"
    r"and\s+(add|remove|include)|"
    r"include|exclude|make\s+it|turn\s+it"
    r")\b",
    re.IGNORECASE,
)


def classify_intent(
    prompt: str,
    has_existing_project: bool,
    message_history: list[dict] | None = None,
) -> Intent:
    """
    Classify user intent from prompt + conversation context.

    Rules (in priority order):
    1. If there's no existing project, always GENERATE.
    2. If the prompt matches retrieve patterns, RETRIEVE.
    3. If there's history (multi-turn) and the prompt has refine patterns, REFINE.
    4. If the prompt has generate patterns, GENERATE.
    5. Default when there IS history: REFINE (assume user is building on it).
    6. Default when no history: GENERATE.
    """
    prompt_lower = prompt.strip().lower()

    if not has_existing_project:
        logger.info(f"[IntentRouter] No existing project → GENERATE")
        return Intent.GENERATE

    if _RETRIEVE_PATTERNS.search(prompt_lower):
        logger.info(f"[IntentRouter] Matched RETRIEVE pattern")
        return Intent.RETRIEVE

    has_history = bool(message_history and len(message_history) > 0)

    if has_history and _REFINE_PATTERNS.search(prompt_lower):
        logger.info(f"[IntentRouter] History + REFINE pattern → REFINE")
        return Intent.REFINE

    if _GENERATE_PATTERNS.search(prompt_lower):
        logger.info(f"[IntentRouter] Matched GENERATE pattern")
        return Intent.GENERATE

    # Default with history = refine; without = generate
    if has_history:
        logger.info(f"[IntentRouter] Has history, defaulting to REFINE")
        return Intent.REFINE

    logger.info(f"[IntentRouter] No pattern matched, defaulting to GENERATE")
    return Intent.GENERATE
