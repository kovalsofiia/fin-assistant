"""Тестові фейки для агента."""


class ScriptedLLM:
    """Фейковий LLMClient: повертає заздалегідь задані відповіді й запам'ятовує запити."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.calls = []

    def complete(self, messages, tools):
        self.calls.append({"messages": [dict(m) for m in messages], "tools": tools})
        return self.turns.pop(0)
