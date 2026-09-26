import pytest
from fastapi.testclient import TestClient

from agent.llm_client import AssistantTurn
from core.auth import get_current_user_id
from main import app
from routers import chat as chat_router
from tests.fakes import ScriptedLLM


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("agent.runner.load_profile_context", lambda user_id: "- Група ФОП: 3")
    monkeypatch.setattr(chat_router.settings, "LLM_MODEL", "a/default")
    monkeypatch.setattr(chat_router.settings, "LLM_MODELS", ["b/fast", "c/smart"])
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    yield TestClient(app)
    app.dependency_overrides.clear()


def use_llm(llm):
    app.dependency_overrides[chat_router.get_llm_client] = lambda: llm
    return llm


def ask(client, **extra):
    return client.post("/chat/", json={"messages": [{"role": "user", "content": "Привіт"}], **extra})


def test_available_models_puts_default_first(client):
    assert chat_router.available_models() == ["a/default", "b/fast", "c/smart"]
    assert chat_router.default_model() == "a/default"


def test_default_model_is_listed_once(client, monkeypatch):
    monkeypatch.setattr(chat_router.settings, "LLM_MODELS", ["b/fast", "a/default"])

    assert chat_router.available_models() == ["b/fast", "a/default"]
    assert chat_router.default_model() == "a/default"


def test_first_whitelisted_model_is_default_without_llm_model(client, monkeypatch):
    monkeypatch.setattr(chat_router.settings, "LLM_MODEL", "")

    assert chat_router.default_model() == "b/fast"


def test_no_models_configured(client, monkeypatch):
    monkeypatch.setattr(chat_router.settings, "LLM_MODEL", "")
    monkeypatch.setattr(chat_router.settings, "LLM_MODELS", [])

    assert client.get("/chat/models").json() == {"models": [], "default": None}


def test_models_endpoint(client):
    response = client.get("/chat/models")

    assert response.status_code == 200
    assert response.json() == {"models": ["a/default", "b/fast", "c/smart"], "default": "a/default"}


def test_models_endpoint_requires_auth():
    assert TestClient(app).get("/chat/models").status_code in (401, 403)


def test_chat_uses_requested_model(client):
    llm = use_llm(ScriptedLLM([AssistantTurn(content="Вітаю!")]))

    response = ask(client, model="c/smart")

    assert response.status_code == 200
    assert response.json()["model"] == "c/smart"
    assert llm.model == "c/smart"


def test_chat_uses_default_model_when_not_given(client):
    llm = use_llm(ScriptedLLM([AssistantTurn(content="Вітаю!")]))

    response = ask(client)

    assert response.json()["model"] == "a/default"
    assert llm.model == "a/default"


def test_chat_rejects_model_outside_whitelist(client):
    llm = use_llm(ScriptedLLM([AssistantTurn(content="x")]))

    response = ask(client, model="expensive/model")

    assert response.status_code == 422
    assert llm.calls == []
