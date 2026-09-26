# Чат-асистент (LLM-агент)

Асистент відповідає на питання користувача про його фінанси й податки ФОП.
Він **лише читає** дані й бере цифри виключно з інструментів (tools).

## Архітектура

```
Vue ChatWidget ──POST /chat/──▶ routers/chat.py ──▶ agent/runner.py (цикл, ≤5 ітерацій)
                                                     ├─▶ agent/llm_client.py ──▶ OpenAI-сумісний API
                                                     └─▶ agent/tools.py ──▶ наявні хендлери routers/*
```

- `llm_client.py` — адаптер над Chat Completions (`openai` SDK + `base_url`).
- `tools.py` — реєстр інструментів; кожен викликає наявний хендлер роутера з `current_user_id` з токена.
- `prompts.py` — системний промпт (українською, заборона вигадувати цифри, дисклеймер для податків) + контекст профілю ФОП.
- `runner.py` — цикл tool calling.
- Бекенд stateless: історію (≤ 20 повідомлень, ≤ 2000 символів кожне) надсилає фронтенд.

Примітка: для користувача без налаштувань ФОП `get_fop_settings` створює рядок налаштувань за замовчуванням (так само, як сторінка налаштувань) — це єдиний запис, який може статися під час роботи агента.

## Налаштування

У `backend/.env` (див. `.env.example`):

| Змінна | Опис |
|---|---|
| `LLM_API_KEY` | Ключ OpenRouter (або будь-який рядок для Ollama) |
| `LLM_BASE_URL` | Типово `https://openrouter.ai/api/v1` |
| `LLM_MODEL` | Ідентифікатор моделі з tool calling, напр. з openrouter.ai/models |
| `LLM_MODELS` | Необов'язково: моделі для вибору в чаті, через кому. `LLM_MODEL` іде першою як модель за замовчуванням. Моделі поза списком ендпоінт відхиляє (`422`) — це захищає бюджет |

Без `LLM_API_KEY` / `LLM_MODEL` ендпоінт повертає `503`.

Локальна модель через Ollama: `LLM_BASE_URL=http://localhost:11434/v1`, `LLM_API_KEY=ollama`, `LLM_MODEL=<назва моделі в ollama>`.

## Тести

```bash
cd backend
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest --cov=agent --cov=routers.chat --cov-report=term-missing
```

LLM, Supabase і НБУ в тестах замокані — мережа не потрібна.

## Як додати інструмент

1. Написати обробник `_my_tool(user_id: str, **args)` у `tools.py`, який викликає наявний хендлер з `current_user_id=user_id`.
2. Додати `Tool(name=..., description=..., parameters=<JSON Schema>, handler=_my_tool)` у список.
3. Покрити тестом у `tests/test_tools.py` (замокати хендлер через `monkeypatch`).

Ніколи не приймати `user_id` з аргументів моделі і не додавати інструменти, що змінюють дані.
