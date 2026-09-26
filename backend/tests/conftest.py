import os

# Задаємо фейкові значення ДО імпорту застосунку: load_dotenv() не перезаписує
# наявні змінні, тож реальні ключі з .env у тести не потраплять.
os.environ["SUPABASE_URL"] = "http://localhost:54321"
os.environ["SUPABASE_KEY"] = "test.test.test"
os.environ["LLM_API_KEY"] = "test-llm-key"
os.environ["LLM_BASE_URL"] = "http://llm.invalid/v1"
os.environ["LLM_MODEL"] = "test-model"
os.environ["LLM_MODELS"] = ""
