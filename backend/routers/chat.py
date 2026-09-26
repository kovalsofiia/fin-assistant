import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from agent.llm_client import LLMClient
from agent.runner import run_agent
from core.auth import get_current_user_id
from core.config import settings

logger = logging.getLogger(__name__)

MAX_HISTORY = 20
MAX_MESSAGE_CHARS = 2000

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    # role "system"/"tool" заборонені: клієнт не може підмінити системний промпт.
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(min_length=1, max_length=MAX_HISTORY)
    model: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    tools_used: List[str]
    model: str


class ModelsResponse(BaseModel):
    models: List[str]
    default: Optional[str]


def available_models() -> List[str]:
    """Моделі, які можна обрати: LLM_MODEL (за замовчуванням) + білий список LLM_MODELS."""
    models = list(settings.LLM_MODELS)
    if settings.LLM_MODEL and settings.LLM_MODEL not in models:
        models.insert(0, settings.LLM_MODEL)
    return models


def default_model() -> Optional[str]:
    models = available_models()
    return settings.LLM_MODEL or (models[0] if models else None)


def get_llm_client() -> LLMClient:
    model = default_model()
    if not settings.LLM_API_KEY or not model:
        raise HTTPException(status_code=503, detail="Чат-асистент не налаштований")
    return LLMClient(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL, model=model)


@router.get("/models", response_model=ModelsResponse)
def list_models(current_user_id: str = Depends(get_current_user_id)):
    """Моделі, доступні для вибору в чаті."""
    return ModelsResponse(models=available_models(), default=default_model())


@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user_id: str = Depends(get_current_user_id),
    llm: LLMClient = Depends(get_llm_client),
):
    """Відповідь асистента на останнє повідомлення користувача."""
    if request.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="Останнє повідомлення має бути від користувача")

    model = request.model or default_model()
    if model not in available_models():
        raise HTTPException(status_code=422, detail="Обрана модель недоступна")
    # get_llm_client створює новий клієнт на кожен запит, тож змінювати його модель безпечно.
    llm.model = model

    history = [message.model_dump() for message in request.messages]
    try:
        result = run_agent(history, current_user_id, llm)
    except Exception:
        logger.exception("Chat agent error")
        raise HTTPException(status_code=502, detail="Помилка звернення до мовної моделі. Спробуйте пізніше.")

    return ChatResponse(reply=result.reply, tools_used=result.tools_used, model=model)
