from datetime import date

from agent import runner
from agent.llm_client import AssistantTurn, ToolCall
from tests.fakes import ScriptedLLM

TODAY = date(2026, 9, 27)
HISTORY = [{"role": "user", "content": "Який у мене баланс?"}]


def run(llm, history=HISTORY, **kwargs):
    return runner.run_agent(history, "user-1", llm, today=TODAY, profile_context="- Група ФОП: 3", **kwargs)


def test_text_reply_without_tools():
    llm = ScriptedLLM([AssistantTurn(content="Привіт!")])

    result = run(llm)

    assert result == runner.AgentResult(reply="Привіт!", tools_used=[])
    sent = llm.calls[0]["messages"]
    assert sent[0]["role"] == "system"
    assert "2026-09-27" in sent[0]["content"]
    assert "- Група ФОП: 3" in sent[0]["content"]
    assert sent[1:] == HISTORY
    assert llm.calls[0]["tools"]


def test_executes_tool_then_answers(monkeypatch):
    executed = []

    def fake_execute(name, arguments, user_id):
        executed.append((name, arguments, user_id))
        return '{"balance": 5}'

    monkeypatch.setattr(runner, "execute_tool", fake_execute)
    llm = ScriptedLLM(
        [
            AssistantTurn(content=None, tool_calls=[ToolCall(id="c1", name="get_transactions_summary", arguments={})]),
            AssistantTurn(content="Ваш баланс 5 грн."),
        ]
    )

    result = run(llm)

    assert result == runner.AgentResult(reply="Ваш баланс 5 грн.", tools_used=["get_transactions_summary"])
    assert executed == [("get_transactions_summary", {}, "user-1")]
    second = llm.calls[1]["messages"]
    assert second[-2]["role"] == "assistant"
    assert second[-2]["tool_calls"][0]["id"] == "c1"
    assert second[-1] == {"role": "tool", "tool_call_id": "c1", "content": '{"balance": 5}'}


def test_multiple_tool_calls_in_one_turn(monkeypatch):
    monkeypatch.setattr(runner, "execute_tool", lambda name, arguments, user_id: "{}")
    llm = ScriptedLLM(
        [
            AssistantTurn(
                content=None,
                tool_calls=[
                    ToolCall(id="a", name="get_insights", arguments={}),
                    ToolCall(id="b", name="get_budgets_progress", arguments={}),
                ],
            ),
            AssistantTurn(content="Готово"),
        ]
    )

    result = run(llm)

    assert result.tools_used == ["get_insights", "get_budgets_progress"]
    assert [m["tool_call_id"] for m in llm.calls[1]["messages"] if m["role"] == "tool"] == ["a", "b"]


def test_caps_tool_calls_per_turn(monkeypatch):
    executed = []
    monkeypatch.setattr(runner, "execute_tool", lambda name, arguments, user_id: executed.append(name) or "{}")
    calls = [ToolCall(id=str(i), name="get_insights", arguments={}) for i in range(10)]
    llm = ScriptedLLM([AssistantTurn(content=None, tool_calls=calls), AssistantTurn(content="Готово")])

    result = run(llm)

    assert len(executed) == runner.MAX_TOOL_CALLS_PER_TURN
    assert len(result.tools_used) == runner.MAX_TOOL_CALLS_PER_TURN
    tool_messages = [m for m in llm.calls[1]["messages"] if m["role"] == "tool"]
    assert len(tool_messages) == 10
    assert [m["tool_call_id"] for m in tool_messages] == [str(i) for i in range(10)]


def test_stops_after_max_iterations(monkeypatch):
    monkeypatch.setattr(runner, "execute_tool", lambda name, arguments, user_id: "{}")
    looping = AssistantTurn(content=None, tool_calls=[ToolCall(id="x", name="get_insights", arguments={})])
    llm = ScriptedLLM([looping] * 10)

    result = run(llm)

    assert result.reply == runner.ITERATION_LIMIT_REPLY
    assert len(llm.calls) == runner.MAX_ITERATIONS


def test_empty_reply_uses_fallback():
    assert run(ScriptedLLM([AssistantTurn(content="   ")])).reply == runner.FALLBACK_REPLY


def test_history_is_not_mutated():
    history = [{"role": "user", "content": "Привіт"}]

    run(ScriptedLLM([AssistantTurn(content="Вітаю")]), history=history)

    assert history == [{"role": "user", "content": "Привіт"}]


def test_loads_profile_context_when_not_given(monkeypatch):
    monkeypatch.setattr(runner, "load_profile_context", lambda user_id: f"- профіль {user_id}")
    llm = ScriptedLLM([AssistantTurn(content="Ок")])

    runner.run_agent(HISTORY, "user-1", llm, today=TODAY)

    assert "- профіль user-1" in llm.calls[0]["messages"][0]["content"]
