"""
PromptToSpecAgent — Converts natural language prompts into validated BackendSpec JSON.

Uses Google Agent Development Kit (ADK) with Gemini to interpret user descriptions
and produce a strict JSON backend specification conforming to our schema.

Model-agnostic: the caller picks the model; the agent falls back automatically
on quota exhaustion (429).
"""

from __future__ import annotations

import asyncio
import json
import logging

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from backend.app.spec_schema import BackendSpec
from backend.agents.model_registry import DEFAULT_MODEL, get_fallback_chain

logger = logging.getLogger(__name__)

# The canonical schema, serialized for the agent prompt
_SPEC_SCHEMA_EXAMPLE = json.dumps(
    {
        "project_name": "string (lowercase, hyphens allowed)",
        "description": "string",
        "spec_version": "1.0",
        "database": {"type": "postgres", "version": "15"},
        "auth": {
            "enabled": True,
            "type": "jwt",
            "access_token_expiry_minutes": 30,
        },
        "entities": [
            {
                "name": "EntityName (PascalCase)",
                "table_name": "entity_names (snake_case, plural)",
                "fields": [
                    {
                        "name": "field_name (snake_case)",
                        "type": "one of: string | integer | float | boolean | datetime | uuid | text",
                        "primary_key": False,
                        "nullable": True,
                        "unique": False,
                    }
                ],
                "crud": True,
            }
        ],
    },
    indent=2,
)

_AGENT_INSTRUCTION = f"""You are a backend specification generator.

Your ONLY job is to convert a user's natural language description of a backend
into a valid JSON object matching the schema below. 

RULES:
1. Return ONLY valid JSON. No markdown, no explanation, no comments.
2. Every entity MUST have exactly one field with "primary_key": true, of type "uuid".
3. Entity names MUST be PascalCase (e.g. "Product", "OrderItem").
4. Table names MUST be snake_case and plural (e.g. "products", "order_items").
5. Field names MUST be snake_case (e.g. "created_at", "user_id").
6. Only these field types are allowed: string, integer, float, boolean, datetime, uuid, text.
7. project_name must be lowercase with hyphens (e.g. "my-api", "blog-backend").
8. Always include spec_version: "1.0".
9. Set auth.enabled to true unless the user explicitly says no authentication.
10. Generate sensible fields based on the user's description. Include common fields
    like created_at (datetime), updated_at (datetime) where appropriate.

SCHEMA:
{_SPEC_SCHEMA_EXAMPLE}

Return ONLY the JSON object. Nothing else."""


def _create_agent(model_id: str) -> Agent:
    """Create a fresh ADK Agent targeting the given model."""
    return Agent(
        name="prompt_to_spec_agent",
        model=model_id,
        description="Converts natural language prompts into backend specification JSON.",
        instruction=_AGENT_INSTRUCTION,
        generate_content_config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )


def _is_quota_error(error: Exception) -> bool:
    """Check whether an error is a 429 / RESOURCE_EXHAUSTED quota error."""
    err_str = str(error)
    return "429" in err_str or "RESOURCE_EXHAUSTED" in err_str


async def _try_generate_with_model(
    model_id: str,
    prompt: str,
    context: str = "",
    messages: list[dict] | None = None,
    max_retries: int = 2,
) -> BackendSpec:
    """
    Attempt to generate a spec using a single model.
    Retries on validation errors; raises on persistent API failures.
    """
    agent = _create_agent(model_id)

    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="backend_generator",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="backend_generator",
        user_id="builder",
    )

    last_error = None

    for attempt in range(1 + max_retries):
        if attempt == 0:
            user_message = ""
            if context:
                user_message += f"CONTEXT FROM UPLOADED DOCUMENTS:\n{context}\n\n"
            if messages:
                user_message += "PREVIOUS CONVERSATION HISTORY (FOR CONTEXT):\n"
                for msg in messages:
                    user_message += f"[{msg['role'].upper()}]: {msg['content']}\n\n"
            
            user_message += f"USER REQUEST:\n{prompt}"
        else:
            user_message = (
                f"Your previous response was invalid JSON or did not match the schema.\n"
                f"Error: {last_error}\n\n"
                f"Please try again. Original request: {prompt}"
            )

        user_content = types.Content(
            role="user",
            parts=[types.Part(text=user_message)],
        )

        agent_response_text = ""

        # Inner retry loop for API calls (networking/transient errors)
        api_success = False
        for api_attempt in range(3):
            try:
                async for event in runner.run_async(
                    user_id="builder",
                    session_id=session.id,
                    new_message=user_content,
                ):
                    if event.is_final_response():
                        if event.content and event.content.parts:
                            agent_response_text = event.content.parts[0].text
                        break
                api_success = True
                break
            except Exception as e:
                if _is_quota_error(e):
                    # Quota exhaustion — don't retry same model, let caller fallback
                    raise
                logger.warning(f"[{model_id}] API attempt {api_attempt + 1} failed: {e}")
                await asyncio.sleep(2 ** api_attempt)

        if not api_success:
            raise RuntimeError(f"[{model_id}] API call failed after 3 attempts")

        if not agent_response_text:
            last_error = "Agent returned empty response"
            logger.warning(f"[{model_id}] Attempt {attempt + 1}: {last_error}")
            continue

        # Clean potential markdown wrapping
        clean_text = agent_response_text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            clean_text = "\n".join(lines)

        try:
            spec_data = json.loads(clean_text)
            spec = BackendSpec(**spec_data)
            logger.info(f"[{model_id}] Spec generated on attempt {attempt + 1}")
            return spec
        except (json.JSONDecodeError, Exception) as e:
            last_error = str(e)
            logger.warning(f"[{model_id}] Attempt {attempt + 1} validation failed: {last_error}")

    raise ValueError(
        f"[{model_id}] Failed to generate valid spec after {1 + max_retries} attempts. "
        f"Last error: {last_error}"
    )


async def generate_spec_from_prompt(
    prompt: str,
    model_id: str | None = None,
    context: str = "",
    messages: list[dict] | None = None,
    max_retries: int = 2,
) -> tuple[BackendSpec, str]:
    """
    Send a natural language prompt to the PromptToSpecAgent and return
    a validated BackendSpec plus the model ID that succeeded.

    Automatically walks the fallback chain on quota exhaustion.

    Args:
        prompt: Natural language description of the desired backend.
        model_id: Starting model (default: DEFAULT_MODEL).
        context: Embedded document context.
        messages: Previous thread messages for conversational context.
        max_retries: Number of retry attempts on invalid output per model.

    Returns:
        Tuple of (validated BackendSpec, model_id that succeeded).

    Raises:
        ValueError: If all models in the chain fail.
    """
    start_model = model_id or DEFAULT_MODEL
    chain = get_fallback_chain(start_model)

    last_error: str | None = None

    for current_model in chain:
        logger.info(f"Trying model: {current_model}")
        try:
            spec = await _try_generate_with_model(
                current_model, prompt, context=context, messages=messages, max_retries=max_retries
            )
            return spec, current_model
        except Exception as e:
            last_error = str(e)
            if _is_quota_error(e) and current_model != chain[-1]:
                logger.warning(
                    f"[{current_model}] Quota exhausted, falling back to next model..."
                )
                continue
            elif current_model != chain[-1]:
                logger.warning(
                    f"[{current_model}] Failed ({last_error}), trying next model..."
                )
                continue
            else:
                logger.error(f"[{current_model}] Final model in chain also failed.")

    raise ValueError(
        f"All models in fallback chain failed. Chain: {chain}. "
        f"Last error: {last_error}"
    )
