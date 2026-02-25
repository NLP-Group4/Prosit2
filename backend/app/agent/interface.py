import re
from typing import Literal

from pydantic import BaseModel, Field
from app.agent.base import BaseAgent
from app.core.config import settings

INTERFACE_SYSTEM_PROMPT = """
You are Interius, the chat interface and intent router for an API/backend code generation assistant.

Your job is to decide whether the user's latest message should trigger the full generation
pipeline or should be handled as normal conversation.

Choose `should_trigger_pipeline=true` only when the user is clearly asking to build/generate/modify
software artifacts (APIs, code, schemas, endpoints, architecture, tests, deployment configs, etc.)
and the request is actionable for the pipeline.

Choose `should_trigger_pipeline=false` for:
- greetings, thanks, acknowledgements
- questions asking for clarification or context only
- conversational responses that do not ask for generation work
- vague prompts that need a follow-up question before generation

Return a concise assistant reply:
- If no pipeline: directly answer or ask a clarifying question.
- If pipeline: acknowledge and say Interius is starting generation.
- Always speak as Interius (use the name "Interius" in the assistant reply).
- Do not prefix replies with a speaker label like "Interius:".
- If an attachment summary indicates `text=no`, Interius only knows the file metadata (not its contents yet).
  Be honest and ask the user to re-upload or paste the relevant portion if content is needed.
- If a build is triggered and any attachment summary has `text=yes` with an excerpt, mention one concrete detail
  from the attached context (briefly) so the acknowledgment shows Interius understood the file context.

If `should_trigger_pipeline=true`, provide `pipeline_prompt` as a cleaned version of the request suitable
for downstream agents. If false, set `pipeline_prompt` to null.

Use recent conversation context when provided to interpret follow-up requests, pronouns, and references
to previously generated files/artifacts.
""".strip()


class InterfaceContextMessage(BaseModel):
    role: Literal["user", "assistant", "agent"]
    content: str = Field(..., min_length=1)


class InterfaceAttachmentSummary(BaseModel):
    filename: str = Field(..., min_length=1)
    mime_type: str | None = None
    size_bytes: int | None = None
    text_excerpt: str | None = None
    has_text_content: bool = False


class InterfaceDecision(BaseModel):
    intent: Literal["pipeline_request", "context_question", "social", "clarification"]
    should_trigger_pipeline: bool
    assistant_reply: str = Field(
        ...,
        description="Short message to show the user before/without pipeline execution.",
    )
    pipeline_prompt: str | None = Field(
        default=None,
        description="Normalized prompt to pass to the orchestrator when pipeline should run.",
    )


class InterfaceAgent(BaseAgent[str, InterfaceDecision]):
    """Routes user messages to either chat response or the generation pipeline."""

    def __init__(self, model_name: str | None = None):
        super().__init__(
            model_name=model_name or settings.MODEL_INTERFACE,
            base_url=settings.INTERFACE_LLM_BASE_URL or None,
            api_key=settings.INTERFACE_LLM_API_KEY or None,
        )

    async def run(
        self,
        input_data: str,
        recent_messages: list[InterfaceContextMessage] | None = None,
        attachment_summaries: list[InterfaceAttachmentSummary] | None = None,
    ) -> InterfaceDecision:
        text = (input_data or "").strip()

        heuristic = self._quick_non_pipeline(text)
        if heuristic:
            return heuristic

        attachment_clarifier = self._quick_attachment_metadata_only_response(
            text, attachment_summaries
        )
        if attachment_clarifier:
            return attachment_clarifier

        if not text and attachment_summaries:
            count = len(attachment_summaries)
            noun = "file" if count == 1 else "files"
            return InterfaceDecision(
                intent="context_question",
                should_trigger_pipeline=False,
                assistant_reply=f"I've noted {count} attached {noun} as thread context. Tell me what you want Interius to build when you're ready.",
                pipeline_prompt=None,
            )

        if not text:
            return InterfaceDecision(
                intent="clarification",
                should_trigger_pipeline=False,
                assistant_reply="Tell me what you want to build or ask a question, and I can help from there.",
                pipeline_prompt=None,
            )

        decision = await self.llm.generate_structured(
            system_prompt=INTERFACE_SYSTEM_PROMPT,
            user_prompt=self._build_user_prompt(text, recent_messages, attachment_summaries),
            response_schema=InterfaceDecision,
        )
        return self._normalize_decision(text, decision, attachment_summaries)

    @staticmethod
    def _build_user_prompt(
        latest_prompt: str,
        recent_messages: list[InterfaceContextMessage] | None,
        attachment_summaries: list[InterfaceAttachmentSummary] | None,
    ) -> str:
        sections: list[str] = []

        trimmed_msgs: list[InterfaceContextMessage] = []
        for msg in (recent_messages or [])[-10:]:
            content = (msg.content or "").strip()
            if not content:
                continue
            trimmed_msgs.append(msg.model_copy(update={"content": content}))

        # Avoid duplicating the latest prompt if the frontend already included it in context.
        if (
            trimmed_msgs
            and trimmed_msgs[-1].role == "user"
            and trimmed_msgs[-1].content == latest_prompt.strip()
        ):
            trimmed_msgs = trimmed_msgs[:-1]

        if trimmed_msgs:
            context_lines = "\n".join(
                f"- {msg.role}: {msg.content}" for msg in trimmed_msgs
            )
            sections.append(
                "Recent conversation context (most recent last):\n"
                f"{context_lines}"
            )

        trimmed_files = (attachment_summaries or [])[-8:]
        if trimmed_files:
            file_lines = []
            for file in trimmed_files:
                parts = [file.filename]
                if file.mime_type:
                    parts.append(file.mime_type)
                if file.size_bytes is not None:
                    parts.append(f"{file.size_bytes} bytes")
                parts.append("text=yes" if file.has_text_content else "text=no")
                line = " | ".join(parts)
                if file.text_excerpt:
                    line += f"\n  excerpt: {file.text_excerpt}"
                file_lines.append(f"- {line}")
            sections.append(
                "Thread attachment summaries (for context only; not full file contents):\n"
                + "\n".join(file_lines)
            )

        sections.append("Latest user message:\n" + latest_prompt)
        return "\n\n".join(sections)

    @staticmethod
    def _normalize_decision(
        original_prompt: str,
        decision: InterfaceDecision,
        attachment_summaries: list[InterfaceAttachmentSummary] | None = None,
    ) -> InterfaceDecision:
        assistant_reply = (decision.assistant_reply or "").strip()
        assistant_reply = re.sub(r"^\s*Interius:\s*", "", assistant_reply, flags=re.IGNORECASE)

        if decision.should_trigger_pipeline:
            pipeline_prompt = (decision.pipeline_prompt or "").strip() or original_prompt.strip()
            assistant_reply = InterfaceAgent._enrich_build_ack_with_attachment_context(
                assistant_reply, attachment_summaries
            )
            return decision.model_copy(
                update={
                    "intent": "pipeline_request",
                    "assistant_reply": assistant_reply or "Interius is starting generation for your request.",
                    "pipeline_prompt": pipeline_prompt,
                }
            )

        return decision.model_copy(
            update={
                "assistant_reply": assistant_reply or "Interius is ready to help.",
                "pipeline_prompt": None,
            }
        )

    @staticmethod
    def _enrich_build_ack_with_attachment_context(
        assistant_reply: str,
        attachment_summaries: list[InterfaceAttachmentSummary] | None,
    ) -> str:
        reply = (assistant_reply or "").strip()
        file_with_text = next(
            (
                f for f in (attachment_summaries or [])
                if f.has_text_content and (f.text_excerpt or "").strip()
            ),
            None,
        )
        if not file_with_text:
            return reply or "Interius is starting generation for your request."

        excerpt = re.sub(r"\s+", " ", (file_with_text.text_excerpt or "")).strip()
        excerpt = excerpt[:140].rstrip(" ,;:-")
        if not excerpt:
            return reply or "Interius is starting generation for your request."

        evidence_line = (
            f'I can see context in `{file_with_text.filename}` (for example: "{excerpt}").'
        )
        if not reply:
            return "Interius is starting generation for your request. " + evidence_line

        if evidence_line.lower() in reply.lower():
            return reply

        # Avoid repetitive over-long acknowledgements.
        if len(reply) > 260:
            return reply

        return f"{reply.rstrip()} {evidence_line}"

    @staticmethod
    def _quick_non_pipeline(text: str) -> InterfaceDecision | None:
        if not text:
            return None

        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        token_count = len(normalized.split())

        gratitude_tokens = {
            "thanks",
            "thank you",
            "thx",
            "ty",
            "appreciate it",
            "awesome thanks",
            "great thanks",
        }
        greeting_tokens = {
            "hi",
            "hello",
            "hey",
            "yo",
            "good morning",
            "good afternoon",
            "good evening",
            "good day",
        }

        if (
            "who are you" in normalized
            or "what do you do" in normalized
            or ("who are you" in normalized and "what" in normalized)
        ):
            return InterfaceDecision(
                intent="context_question",
                should_trigger_pipeline=False,
                assistant_reply=(
                    "I'm Interius. I can answer questions directly, help clarify requirements, "
                    "and start the build pipeline when you want APIs, code, schemas, configs, or related backend artifacts."
                ),
                pipeline_prompt=None,
            )

        if normalized in gratitude_tokens or normalized.rstrip("!.") in gratitude_tokens:
            return InterfaceDecision(
                intent="social",
                should_trigger_pipeline=False,
                assistant_reply="You're welcome. If you want, send the next feature or bug fix request and Interius will route it correctly.",
                pipeline_prompt=None,
            )

        if token_count <= 4 and normalized.rstrip("!.?") in greeting_tokens:
            return InterfaceDecision(
                intent="social",
                should_trigger_pipeline=False,
                assistant_reply="Hi. Tell me what you need help with, and I can answer directly or start the build pipeline if you want me to generate something.",
                pipeline_prompt=None,
            )

        return None

    @staticmethod
    def _quick_attachment_metadata_only_response(
        text: str,
        attachment_summaries: list[InterfaceAttachmentSummary] | None,
    ) -> InterfaceDecision | None:
        if not text or not attachment_summaries:
            return None

        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        mentions_attachment = any(
            token in normalized
            for token in ("attach", "attachment", "document", "pdf", "file", "there", "it")
        )
        asks_for_contents = any(
            token in normalized
            for token in ("read", "see", "what is in", "what's in", "use it", "use that", "summarize", "extract")
        )

        if not (mentions_attachment and asks_for_contents):
            return None

        if any(file.has_text_content for file in attachment_summaries):
            return None

        latest = attachment_summaries[-1]
        file_label = latest.filename if latest.filename else "the previously attached file"
        return InterfaceDecision(
            intent="clarification",
            should_trigger_pipeline=False,
            assistant_reply=(
                f"I can see metadata for `{file_label}`, but I don't currently have its contents in this session. "
                "Please re-upload it (or paste the relevant section) if you want Interius to use it."
            ),
            pipeline_prompt=None,
        )
