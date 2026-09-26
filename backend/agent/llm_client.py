"""Тонкий адаптер над OpenAI-сумісним Chat Completions API (OpenRouter, Ollama тощо)."""
import json
from dataclasses import dataclass, field
from typing import Any, Optional

from openai import OpenAI


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class AssistantTurn:
    content: Optional[str]
    tool_calls: list = field(default_factory=list)

    def to_message(self) -> dict:
        """Повідомлення асистента у форматі Chat Completions для наступного запиту."""
        message = {"role": "assistant", "content": self.content or ""}
        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments, ensure_ascii=False),
                    },
                }
                for call in self.tool_calls
            ]
        return message


def _parse_arguments(raw: Optional[str]) -> dict:
    # Модель може повернути невалідний JSON — тоді tool отримає {} і поверне помилку аргументів.
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


class LLMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float = 0.2,
        sdk_client: Any = None,
    ):
        self.model = model
        self.temperature = temperature
        self._client = sdk_client or OpenAI(api_key=api_key, base_url=base_url)

    def complete(self, messages: list, tools: list) -> AssistantTurn:
        kwargs = {"model": self.model, "messages": messages, "temperature": self.temperature}
        if tools:
            kwargs["tools"] = tools
        response = self._client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        tool_calls = [
            ToolCall(id=call.id, name=call.function.name, arguments=_parse_arguments(call.function.arguments))
            for call in (message.tool_calls or [])
        ]
        return AssistantTurn(content=message.content, tool_calls=tool_calls)
