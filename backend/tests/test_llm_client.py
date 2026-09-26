from types import SimpleNamespace

from agent.llm_client import AssistantTurn, LLMClient, ToolCall


class FakeCompletions:
    def __init__(self, message):
        self.message = message
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=self.message)])


def make_client(message):
    completions = FakeCompletions(message)
    sdk = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    client = LLMClient(api_key="k", base_url="http://x/v1", model="m", sdk_client=sdk)
    return client, completions


def test_complete_returns_text_reply():
    client, completions = make_client(SimpleNamespace(content="Привіт", tool_calls=None))

    turn = client.complete([{"role": "user", "content": "hi"}], tools=[])

    assert turn == AssistantTurn(content="Привіт", tool_calls=[])
    assert completions.kwargs["model"] == "m"
    assert completions.kwargs["temperature"] == 0.2
    assert completions.kwargs["messages"] == [{"role": "user", "content": "hi"}]
    assert completions.kwargs["max_tokens"] == 1024
    assert "tools" not in completions.kwargs


def test_complete_parses_tool_calls_and_passes_tools():
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="get_insights", arguments='{"start_date": "2026-09-01"}'),
    )
    client, completions = make_client(SimpleNamespace(content=None, tool_calls=[tool_call]))
    tools = [{"type": "function", "function": {"name": "get_insights"}}]

    turn = client.complete([{"role": "user", "content": "hi"}], tools=tools)

    assert turn.content is None
    assert turn.tool_calls == [
        ToolCall(id="call_1", name="get_insights", arguments={"start_date": "2026-09-01"})
    ]
    assert completions.kwargs["tools"] == tools


def test_invalid_tool_arguments_become_empty_dict():
    broken = SimpleNamespace(id="c", function=SimpleNamespace(name="x", arguments="not json"))
    not_object = SimpleNamespace(id="d", function=SimpleNamespace(name="y", arguments="[1, 2]"))
    client, _ = make_client(SimpleNamespace(content=None, tool_calls=[broken, not_object]))

    turn = client.complete([], tools=[{"type": "function"}])

    assert [c.arguments for c in turn.tool_calls] == [{}, {}]


def test_to_message_serializes_tool_calls():
    turn = AssistantTurn(
        content=None,
        tool_calls=[ToolCall(id="c1", name="list_categories", arguments={"a": "б"})],
    )

    assert turn.to_message() == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "c1",
                "type": "function",
                "function": {"name": "list_categories", "arguments": '{"a": "б"}'},
            }
        ],
    }


def test_to_message_without_tool_calls():
    assert AssistantTurn(content="Текст").to_message() == {"role": "assistant", "content": "Текст"}


def test_constructs_sdk_client_with_short_timeout_and_no_retries(monkeypatch):
    recorded = {}

    class RecordingOpenAI:
        def __init__(self, **kwargs):
            recorded.update(kwargs)

    monkeypatch.setattr("agent.llm_client.OpenAI", RecordingOpenAI)

    LLMClient(api_key="k", base_url="http://x/v1", model="m")

    assert recorded["timeout"] == 30
    assert recorded["max_retries"] == 1
