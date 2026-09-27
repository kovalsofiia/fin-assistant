"""Цикл агента: LLM → виклики tools → LLM … до текстової відповіді або ліміту ітерацій."""
import json
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from agent.prompts import build_system_prompt, load_profile_context
from agent.tools import run_tool, tool_schemas

MAX_ITERATIONS = 5
MAX_TOOL_CALLS_PER_TURN = 8
TOO_MANY_TOOL_CALLS_REPLY = {"error": "Забагато викликів інструментів за раз"}
MAX_ATTACHMENTS = 3
TOO_MANY_ATTACHMENTS_REPLY = {"error": "Забагато графіків або чернеток в одній відповіді"}
FALLBACK_REPLY = "Не вдалося сформувати відповідь. Спробуйте переформулювати запитання."
ITERATION_LIMIT_REPLY = (
    "Запит виявився занадто складним для однієї відповіді. Спробуйте розбити його на простіші запитання."
)


@dataclass
class AgentResult:
    reply: str
    tools_used: list = field(default_factory=list)
    attachments: list = field(default_factory=list)


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
    attachments = []

    for _ in range(max_iterations):
        turn = llm.complete(messages, schemas)
        if not turn.tool_calls:
            reply = (turn.content or "").strip() or FALLBACK_REPLY
            return AgentResult(reply=reply, tools_used=tools_used, attachments=attachments)

        messages.append(turn.to_message())
        for index, call in enumerate(turn.tool_calls):
            if index >= MAX_TOOL_CALLS_PER_TURN:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(TOO_MANY_TOOL_CALLS_REPLY, ensure_ascii=False),
                    }
                )
                continue
            tools_used.append(call.name)
            content, attachment = run_tool(call.name, call.arguments, user_id)
            if attachment is not None:
                if len(attachments) < MAX_ATTACHMENTS:
                    attachments.append(attachment)
                else:
                    content = json.dumps(TOO_MANY_ATTACHMENTS_REPLY, ensure_ascii=False)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": content})

    return AgentResult(reply=ITERATION_LIMIT_REPLY, tools_used=tools_used, attachments=attachments)
