"""
Tests for PromptToSpecAgent — validates spec generation with mocked LLM.

All tests mock the ADK Runner so no real API calls are made.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.spec_schema import BackendSpec
from agents.prompt_to_spec import (
    generate_spec_from_prompt,
    _try_generate_with_model,
    _is_quota_error,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_SPEC_JSON = json.dumps({
    "project_name": "test-api",
    "description": "A test backend",
    "spec_version": "1.0",
    "database": {"type": "postgres", "version": "15"},
    "auth": {"enabled": True, "type": "jwt", "access_token_expiry_minutes": 30},
    "entities": [
        {
            "name": "Item",
            "table_name": "items",
            "fields": [
                {"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True},
                {"name": "title", "type": "string", "nullable": False},
            ],
            "crud": True,
        }
    ],
})

INVALID_JSON = "This is not JSON {{{}"

MARKDOWN_WRAPPED_JSON = f"```json\n{VALID_SPEC_JSON}\n```"


def _make_final_event(text: str):
    """Create a mock event that mimics ADK's final response event."""
    event = MagicMock()
    event.is_final_response.return_value = True
    event.content = MagicMock()
    event.content.parts = [MagicMock(text=text)]
    return event


def _make_non_final_event():
    """Create a mock non-final event (should be skipped)."""
    event = MagicMock()
    event.is_final_response.return_value = False
    return event


# ---------------------------------------------------------------------------
# _is_quota_error
# ---------------------------------------------------------------------------

class TestIsQuotaError:
    def test_429_detected(self):
        assert _is_quota_error(Exception("HTTP 429 Too Many Requests"))

    def test_resource_exhausted_detected(self):
        assert _is_quota_error(Exception("RESOURCE_EXHAUSTED"))

    def test_normal_error_not_detected(self):
        assert not _is_quota_error(Exception("Connection timeout"))

    def test_empty_error(self):
        assert not _is_quota_error(Exception(""))


# ---------------------------------------------------------------------------
# _try_generate_with_model (mocked LLM)
# ---------------------------------------------------------------------------

class TestTryGenerateWithModel:
    @pytest.mark.asyncio
    async def test_valid_response_returns_spec(self):
        """A valid JSON response should parse into a BackendSpec."""
        final_event = _make_final_event(VALID_SPEC_JSON)

        async def mock_run_async(**kwargs):
            yield final_event

        with patch("agents.prompt_to_spec.Runner") as MockRunner, \
             patch("agents.prompt_to_spec.InMemorySessionService") as MockSS:
            mock_session = MagicMock()
            mock_session.id = "test-session"
            MockSS.return_value.create_session = AsyncMock(return_value=mock_session)
            MockRunner.return_value.run_async = mock_run_async

            spec = await _try_generate_with_model("gemini-2.0-flash", "Build a test API")
            assert isinstance(spec, BackendSpec)
            assert spec.project_name == "test-api"

    @pytest.mark.asyncio
    async def test_markdown_wrapped_json_cleaned(self):
        """JSON wrapped in markdown fences should be cleaned and parsed."""
        final_event = _make_final_event(MARKDOWN_WRAPPED_JSON)

        async def mock_run_async(**kwargs):
            yield final_event

        with patch("agents.prompt_to_spec.Runner") as MockRunner, \
             patch("agents.prompt_to_spec.InMemorySessionService") as MockSS:
            mock_session = MagicMock()
            mock_session.id = "test-session"
            MockSS.return_value.create_session = AsyncMock(return_value=mock_session)
            MockRunner.return_value.run_async = mock_run_async

            spec = await _try_generate_with_model("gemini-2.0-flash", "Build a test API")
            assert isinstance(spec, BackendSpec)

    @pytest.mark.asyncio
    async def test_invalid_json_retries_then_fails(self):
        """Invalid JSON should trigger retries; if all fail, raise ValueError."""
        final_event = _make_final_event(INVALID_JSON)

        async def mock_run_async(**kwargs):
            yield final_event

        with patch("agents.prompt_to_spec.Runner") as MockRunner, \
             patch("agents.prompt_to_spec.InMemorySessionService") as MockSS:
            mock_session = MagicMock()
            mock_session.id = "test-session"
            MockSS.return_value.create_session = AsyncMock(return_value=mock_session)
            MockRunner.return_value.run_async = mock_run_async

            with pytest.raises(ValueError, match="Failed to generate valid spec"):
                await _try_generate_with_model(
                    "gemini-2.0-flash", "Build a test API", max_retries=1
                )

    @pytest.mark.asyncio
    async def test_quota_error_raised_immediately(self):
        """429 errors should be raised immediately (no retry on same model)."""
        async def mock_run_async(**kwargs):
            raise Exception("429 RESOURCE_EXHAUSTED quota exceeded")
            yield  # Make it an async generator

        with patch("agents.prompt_to_spec.Runner") as MockRunner, \
             patch("agents.prompt_to_spec.InMemorySessionService") as MockSS:
            mock_session = MagicMock()
            mock_session.id = "test-session"
            MockSS.return_value.create_session = AsyncMock(return_value=mock_session)
            MockRunner.return_value.run_async = mock_run_async

            with pytest.raises(Exception, match="429"):
                await _try_generate_with_model("gemini-2.0-flash", "Build a test API")

    @pytest.mark.asyncio
    async def test_empty_response_retries(self):
        """Empty responses should trigger retries."""
        call_count = 0
        empty_event = _make_final_event("")
        valid_event = _make_final_event(VALID_SPEC_JSON)

        async def mock_run_async(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                yield empty_event
            else:
                yield valid_event

        with patch("agents.prompt_to_spec.Runner") as MockRunner, \
             patch("agents.prompt_to_spec.InMemorySessionService") as MockSS:
            mock_session = MagicMock()
            mock_session.id = "test-session"
            MockSS.return_value.create_session = AsyncMock(return_value=mock_session)
            MockRunner.return_value.run_async = mock_run_async

            spec = await _try_generate_with_model(
                "gemini-2.0-flash", "Build a test API", max_retries=2
            )
            assert isinstance(spec, BackendSpec)


# ---------------------------------------------------------------------------
# generate_spec_from_prompt (fallback chain)
# ---------------------------------------------------------------------------

class TestGenerateSpecFromPrompt:
    @pytest.mark.asyncio
    async def test_success_returns_spec_and_model(self):
        """Successful generation returns (BackendSpec, model_id) tuple."""
        expected_spec = BackendSpec(**json.loads(VALID_SPEC_JSON))

        with patch("agents.prompt_to_spec._try_generate_with_model",
                    new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = expected_spec

            spec, model_used = await generate_spec_from_prompt("Build a test API")
            assert isinstance(spec, BackendSpec)
            assert model_used == "gemini-2.0-flash"

    @pytest.mark.asyncio
    async def test_quota_fallback_chain(self):
        """When first model hits quota, should try next in fallback chain."""
        expected_spec = BackendSpec(**json.loads(VALID_SPEC_JSON))
        call_models = []

        async def mock_generate(model_id, prompt, context="", max_retries=2):
            call_models.append(model_id)
            if model_id == "gemini-2.0-flash":
                raise Exception("429 RESOURCE_EXHAUSTED")
            return expected_spec

        with patch("agents.prompt_to_spec._try_generate_with_model",
                    side_effect=mock_generate):
            spec, model_used = await generate_spec_from_prompt("Build a test API")
            assert model_used == "gemini-2.5-flash"
            assert "gemini-2.0-flash" in call_models

    @pytest.mark.asyncio
    async def test_all_models_fail_raises(self):
        """If all models in the chain fail, should raise ValueError."""
        async def mock_generate(model_id, prompt, max_retries=2):
            raise Exception("429 RESOURCE_EXHAUSTED")

        with patch("agents.prompt_to_spec._try_generate_with_model",
                    side_effect=mock_generate):
            with pytest.raises(ValueError, match="All models in fallback chain failed"):
                await generate_spec_from_prompt("Build a test API")

    @pytest.mark.asyncio
    async def test_custom_model_id_used(self):
        """A custom model_id should be used as the starting point."""
        expected_spec = BackendSpec(**json.loads(VALID_SPEC_JSON))

        with patch("agents.prompt_to_spec._try_generate_with_model",
                    new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = expected_spec

            spec, model_used = await generate_spec_from_prompt(
                "Build a test API", model_id="gemini-2.5-pro"
            )
            assert model_used == "gemini-2.5-pro"
