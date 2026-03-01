from app.agent.artifacts import ProjectCharter
from app.agent.base import BaseAgent
from app.agent.prompts.requirements import REQUIREMENTS_SYSTEM_PROMPT


class RequirementsAgent(BaseAgent[str, ProjectCharter]):
    """
    Agent responsible for extracting a structured ProjectCharter
    from a user's raw prompt plus document context.
    """

    async def run(self, input_data: str) -> ProjectCharter:
        """
        Processes the input text and returns a structured ProjectCharter artifact.
        `input_data` is the combined text from the user's prompt and any injected RAG context.
        """
        charter = await self.llm.generate_structured(
            system_prompt=REQUIREMENTS_SYSTEM_PROMPT,
            user_prompt=input_data,
            response_schema=ProjectCharter,
            task_name="Requirements Analyzer",
        )

        # Post-validation: If empty, gracefully inject defaults instead of crashing.
        if not charter.entities:
            from app.agent.artifacts import Entity, EntityField
            charter.entities = [
                Entity(
                    name="Item",
                    fields=[
                        EntityField(name="id", field_type="int", required=True),
                        EntityField(name="name", field_type="str", required=True),
                    ]
                )
            ]
        if not charter.endpoints:
            from app.agent.artifacts import Endpoint
            charter.endpoints = [
                Endpoint(method="GET", path="/items", description="List all items"),
                Endpoint(method="POST", path="/items", description="Create an item")
            ]

        return charter
