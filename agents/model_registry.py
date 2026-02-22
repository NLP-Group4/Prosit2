"""
Model Registry — Provider-agnostic model catalog with fallback chains.

This is the single source of truth for which models the platform supports.
Designed to be extended with additional providers (OpenAI, Anthropic, etc.)
when BYOK is implemented.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    """Metadata for a single LLM model."""
    id: str
    name: str
    provider: str        # "google" | future: "openai", "anthropic"
    tier: str            # "free" | "paid"
    description: str
    fallback: str | None  # Model ID to try on 429 / quota exhaustion


# ---------------------------------------------------------------------------
# Model catalog — order doesn't matter; fallback chains are explicit.
# ---------------------------------------------------------------------------

MODELS: dict[str, ModelInfo] = {
    "gemini-2.0-flash": ModelInfo(
        id="gemini-2.0-flash",
        name="Gemini 2.0 Flash",
        provider="google",
        tier="free",
        description="Always-free model with generous rate limits. Best for reliability.",
        fallback="gemini-2.5-flash",  # Fall back UP on quota exhaustion
    ),
    "gemini-2.5-flash": ModelInfo(
        id="gemini-2.5-flash",
        name="Gemini 2.5 Flash",
        provider="google",
        tier="free",
        description="Fast and capable. Free tier with moderate rate limits.",
        fallback="gemini-2.5-pro",
    ),
    "gemini-2.5-pro": ModelInfo(
        id="gemini-2.5-pro",
        name="Gemini 2.5 Pro",
        provider="google",
        tier="free",
        description="Most capable model. Free tier with strict rate limits.",
        fallback=None,  # Terminal — no further fallback
    ),
}

DEFAULT_MODEL = "gemini-2.0-flash"


def get_model(model_id: str) -> ModelInfo:
    """Look up a model by ID. Raises KeyError if not found."""
    if model_id not in MODELS:
        raise KeyError(
            f"Unknown model '{model_id}'. "
            f"Available: {', '.join(MODELS.keys())}"
        )
    return MODELS[model_id]


def get_fallback_chain(model_id: str) -> list[str]:
    """
    Return the ordered fallback chain starting from model_id.

    Example: get_fallback_chain("gemini-2.5-pro")
    → ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]
    """
    chain: list[str] = []
    visited: set[str] = set()
    current: str | None = model_id

    while current and current not in visited:
        if current not in MODELS:
            break
        visited.add(current)
        chain.append(current)
        current = MODELS[current].fallback

    return chain


def list_models() -> list[dict]:
    """Return all models as serializable dicts (for the /models API)."""
    return [
        {
            "id": m.id,
            "name": m.name,
            "provider": m.provider,
            "tier": m.tier,
            "description": m.description,
            "is_default": m.id == DEFAULT_MODEL,
        }
        for m in MODELS.values()
    ]
