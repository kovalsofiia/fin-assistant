import logging
from typing import List, Literal

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


class ChatResponse(BaseModel):
    reply: str
    tools_used: List[str]


def get_llm_client() -> LLMClient:
    if not settings.LLM_API_KEY or not settings.LLM_MODEL:
        raise HTTPException(status_code=503, detail="Чат-асистент не налаштований")
    return LLMClient(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL, model=settings.LLM_MODEL)


@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user_id: str = Depends(get_current_user_id),
    llm: LLMClient = Depends(get_llm_client),
):
    """Відповідь асистента на останнє повідомлення користувача."""
    if request.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="Останнє повідомлення має бути від користувача")

    history = [message.model_dump() for message in request.messages]
    try:
        result = run_agent(history, current_user_id, llm)
    except Exception:
        logger.exception("Chat agent error")
        raise HTTPException(status_code=502, detail="Помилка звернення до мовної моделі. Спробуйте пізніше.")

    return ChatResponse(reply=result.reply, tools_used=result.tools_used)
