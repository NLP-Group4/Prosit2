"""
Tests for agents.model_registry — model catalog, fallback chains, defaults.
"""

import pytest

from backend.agents.model_registry import (
    DEFAULT_MODEL,
    MODELS,
    get_model,
    get_fallback_chain,
    list_models,
)


class TestGetModel:
    def test_known_model(self):
        m = get_model("gemini-2.0-flash")
        assert m.id == "gemini-2.0-flash"
        assert m.provider == "google"

    def test_unknown_model_raises(self):
        with pytest.raises(KeyError, match="Unknown model"):
            get_model("gpt-4o")

    def test_all_registered_models_retrievable(self):
        for model_id in MODELS:
            m = get_model(model_id)
            assert m.id == model_id


class TestFallbackChain:
    def test_pro_chain(self):
        chain = get_fallback_chain("gemini-2.5-pro")
        assert chain == ["gemini-2.5-pro"]  # Terminal — no further fallback

    def test_flash_chain(self):
        chain = get_fallback_chain("gemini-2.5-flash")
        assert chain == ["gemini-2.5-flash", "gemini-2.5-pro"]

    def test_terminal_model_chain(self):
        chain = get_fallback_chain("gemini-2.0-flash")
        assert chain == ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]

    def test_unknown_model_returns_empty(self):
        chain = get_fallback_chain("nonexistent")
        assert chain == []

    def test_no_infinite_loops(self):
        """Ensure the chain terminates even with a hypothetical cycle."""
        for model_id in MODELS:
            chain = get_fallback_chain(model_id)
            assert len(chain) <= len(MODELS)
            assert len(chain) == len(set(chain))  # No duplicates


class TestListModels:
    def test_returns_all_models(self):
        models = list_models()
        assert len(models) == len(MODELS)

    def test_has_required_fields(self):
        for m in list_models():
            assert "id" in m
            assert "name" in m
            assert "provider" in m
            assert "tier" in m
            assert "description" in m
            assert "is_default" in m

    def test_exactly_one_default(self):
        defaults = [m for m in list_models() if m["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["id"] == DEFAULT_MODEL


class TestDefaultModel:
    def test_default_is_free_tier(self):
        m = get_model(DEFAULT_MODEL)
        assert m.tier == "free"

    def test_default_exists_in_registry(self):
        assert DEFAULT_MODEL in MODELS
