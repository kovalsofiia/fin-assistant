"""Моделі-кандидати для пілотного експерименту та їхні ціни на OpenRouter (за 1М токенів, USD).

Ціни зафіксовані на 2026-09-27 (openrouter.ai/models) — можуть змінитися; для точної
вартості кожного запуску харнес усе одно бере prompt/completion tokens з відповіді API.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    id: str  # ідентифікатор моделі на OpenRouter, напр. "google/gemini-3.5-flash-lite"
    label: str  # коротка назва для таблиць і графіків
    price_prompt_per_m: float  # $ за 1M вхідних токенів
    price_completion_per_m: float  # $ за 1M вихідних токенів


PILOT_MODELS = [
    ModelSpec("google/gemini-3.5-flash-lite", "Gemini 3.5 Flash Lite", 0.30, 2.50),
    ModelSpec("openai/gpt-5.6-luna", "GPT-5.6 Luna", 0.20, 1.20),
    ModelSpec("deepseek/deepseek-v4-flash", "DeepSeek V4 Flash", 0.05, 0.09),
]

REPEATS_PER_MODEL = 2
REQUEST_TIMEOUT_S = 60
TEMPERATURE = 0.2


def estimate_cost_usd(model: ModelSpec, prompt_tokens: int, completion_tokens: int) -> float:
    return (prompt_tokens / 1_000_000) * model.price_prompt_per_m + (
        completion_tokens / 1_000_000
    ) * model.price_completion_per_m
