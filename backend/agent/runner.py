"""Цикл агента: LLM → виклики tools → LLM … до текстової відповіді або ліміту ітерацій."""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from agent.prompts import build_system_prompt, load_profile_context
from agent.tools import execute_tool, tool_schemas

MAX_ITERATIONS = 5
FALLBACK_REPLY = "Не вдалося сформувати відповідь. Спробуйте переформулювати запитання."
ITERATION_LIMIT_REPLY = (
    "Запит виявився занадто складним для однієї відповіді. Спробуйте розбити його на простіші запитання."
)


@dataclass
class AgentResult:
    reply: str
    tools_used: list = field(default_factory=list)


def run_agent(
    history: list,
    user_id: str,
    llm,
    today: Optional[date] = None,
    profile_context: Optional[str] = None,
    max_iterations: int = MAX_ITERATIONS,
) -> AgentResult:
    if profile_context is None:
        profile_context = load_profile_context(user_id)
    system = {"role": "system", "content": build_system_prompt(today or date.today(), profile_context)}
    messages = [system, *history]
    schemas = tool_schemas()
    tools_used = []

    for _ in range(max_iterations):
        turn = llm.complete(messages, schemas)
        if not turn.tool_calls:
            return AgentResult(reply=(turn.content or "").strip() or FALLBACK_REPLY, tools_used=tools_used)

        messages.append(turn.to_message())
        for call in turn.tool_calls:
            tools_used.append(call.name)
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": execute_tool(call.name, call.arguments, user_id)}
            )

    return AgentResult(reply=ITERATION_LIMIT_REPLY, tools_used=tools_used)
