import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_PROMPT = """
You are a friendly assistant helping a non-technical user describe an API they want built.
The user is not a developer — they don't know what HTTP methods, endpoints, JWT, or 
databases are. Your job is to have a simple, natural conversation to understand what 
they need, then translate it into a technical spec yourself.

## Your mental checklist
You must gather ALL of the following before finishing:
- project_name: a short slug for the project (e.g. "todo-api")
- description: what the API does in one or two sentences
- endpoints: derived by YOU from what the user describes — never ask them to define these
- auth: decided by YOU based on what makes sense for their use case
- database: decided by YOU based on what makes sense for their use case
- extra: any special requirements the user mentions

## How to behave
- Use plain, simple English — no technical jargon whatsoever
- Ask short, friendly questions — one at a time
- Ask about features and needs, never about technical implementation
- Make all technical decisions yourself (endpoints, auth type, database)
- If the user asks for your recommendation, always give one confidently
- Keep your responses short — two to four sentences maximum
- If they volunteer information early, don't ask for it again
- Once you have everything, summarize in plain English and ask them to confirm

## Example of what NOT to do
Bad: "What HTTP method would you use for adding a todo? e.g. POST /todos"
Good: "What actions should users be able to do with their todo items? 
       For example, add new ones, mark them done, delete them?"

## Finishing
When the user confirms the summary, output the spec in this exact format and nothing else after it:

REQUIREMENTS_COMPLETE
```json
{
  "project_name": "...",
  "description": "...",
  "endpoints": [
    {"method": "GET", "path": "/...", "description": "..."}
  ],
  "auth": "...",
  "database": "...",
  "extra": "..."
}
```
REQUIREMENTS_COMPLETE

Do not produce this output until the user has explicitly confirmed the summary.
The JSON is for internal use — never show or explain it to the user.
"""


def extract_spec(text: str) -> dict | None:
    """
    Looks for the REQUIREMENTS_COMPLETE block in the agent's response
    and parses the JSON spec out of it.
    """
    if "REQUIREMENTS_COMPLETE" not in text:
        return None
    try:
        start = text.index("```json") + 7
        end = text.index("```", start)
        json_str = text[start:end].strip()
        return json.loads(json_str)
    except (ValueError, json.JSONDecodeError):
        return None


def save_spec(spec: dict):
    """Saves the final spec to a JSON file."""
    filename = f"{spec.get('project_name', 'spec')}.json"
    with open(filename, "w") as f:
        json.dump(spec, f, indent=2)
    print(f"\n[Spec saved to {filename}]")
    return filename


def run_agent():
    print("=" * 60)
    print("API Requirements Agent")
    print("Type your responses below. Type 'exit' to quit.")
    print("=" * 60)

    # Start the conversation history
    contents = []

    # Kick off with the agent's opening question
    opening = types.Content(
        role="user",
        parts=[types.Part(text="Hello, I'd like to build an API.")]
    )
    contents.append(opening)

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
    )

    while True:
        # Get agent response
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]
        contents.append(candidate.content)

        # Extract the text response
        agent_text = next(
            (p.text for p in candidate.content.parts if hasattr(p, "text")),
            ""
        )

        # Check if the agent has finished gathering requirements
        spec = extract_spec(agent_text)
        if spec:
            # Print everything before the JSON block
            visible_text = agent_text[:agent_text.index("REQUIREMENTS_COMPLETE")].strip()
            if visible_text:
                print(f"\nAgent: {visible_text}")
            print("\n[Requirements complete! Here is your spec:]")
            print(json.dumps(spec, indent=2))
            filename = save_spec(spec)
            print(f"\n[This spec would now be passed to the Architecture Agent]")
            return spec

        # Normal conversational response
        print(f"\nAgent: {agent_text}")

        # Get user input
        user_input = input("\nYou: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("Exiting.")
            return None
        if not user_input:
            continue

        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=user_input)]
        ))


if __name__ == "__main__":
    run_agent()