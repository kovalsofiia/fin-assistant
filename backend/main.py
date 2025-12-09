import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from pydantic import BaseModel

# 1. Завантажуємо ключі з файлу .env
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# Перевірка, чи є ключі
if not url or not key:
    raise ValueError("Помилка: Не знайдено SUPABASE_URL або SUPABASE_KEY у файлі .env")

# 2. Підключаємось до Supabase
supabase: Client = create_client(url, key)

# 3. Ініціалізуємо FastAPI
app = FastAPI(title="FOP Assistant API")

# Налаштування CORS (Дозволяємо фронтенду стукатись сюди)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Адреса Vue додатку
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Ендпоінти (API) ---

@app.get("/")
def read_root():
    return {"status": "active", "service": "FOP Assistant Tax Engine"}

@app.get("/test-db")
def test_database_connection():
    """
    Перевіряє зв'язок з базою: завантажує список профілів.
    """
    try:
        # Робимо запит в таблицю 'profiles'
        response = supabase.table("profiles").select("*").execute()
        return {
            "message": "Зв'язок з базою успішний!",
            "data": response.data
        }
    except Exception as e:
        return {"error": str(e)}