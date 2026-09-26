import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "FOP Assistant API 🇺🇦"
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")

    # LLM: OpenRouter або будь-який OpenAI-сумісний API (напр. Ollama: http://localhost:11434/v1)
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "")
    # Білий список моделей, з яких користувач може обрати в чаті (через кому)
    LLM_MODELS: list = [m.strip() for m in os.getenv("LLM_MODELS", "").split(",") if m.strip()]

    # Default CORS origins
    DEFAULT_CORS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174"
    ]
    
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else DEFAULT_CORS

settings = Settings()
