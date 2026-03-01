from app.agent.artifacts import GeneratedTests, SystemArchitecture, GeneratedCode
from app.agent.base import BaseAgent
from app.agent.prompts.test_generator import TEST_GENERATOR_SYSTEM_PROMPT
from app.core.config import settings


class TestGeneratorAgent(BaseAgent[SystemArchitecture, GeneratedTests]):
    """
    Agent that generates pytest test suites from the architecture document
    and generated code, so the sandbox can run real endpoint tests.
    """

    def __init__(self):
        super().__init__(model_name=settings.MODEL_DEFAULT)

    async def run(
        self,
        architecture: SystemArchitecture,
        code: GeneratedCode | None = None,
    ) -> GeneratedTests:
        """
        Generate pytest tests based on the architecture doc and optionally
        the generated code (so tests match actual route paths/models).
        """
        prompt = "## Architecture Document\n"
        prompt += architecture.design_document + "\n\n"

        if architecture.endpoint_summary:
            prompt += "## Endpoint Summary\n"
            for ep in architecture.endpoint_summary:
                prompt += f"- {ep}\n"
            prompt += "\n"

        if architecture.data_model_summary:
            prompt += "## Data Models\n"
            for dm in architecture.data_model_summary:
                prompt += f"- {dm}\n"
            prompt += "\n"

        if code and code.files:
            prompt += "## Generated Code Files (for reference — test against these)\n"
            for f in code.files:
                prompt += f"\n--- {f.path} ---\n{f.content}\n"

        prompt += (
            "\n\nGenerate a comprehensive pytest test suite that tests every "
            "endpoint defined above. Return a GeneratedTests artifact."
        )

        return await self.llm.generate_structured(
            system_prompt=TEST_GENERATOR_SYSTEM_PROMPT,
            user_prompt=prompt,
            response_schema=GeneratedTests,
            task_name="Test Generator",
        )
