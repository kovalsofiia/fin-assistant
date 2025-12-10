import os
import requests # Бібліотека для запитів до НБУ
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from pydantic import BaseModel
from datetime import date
from typing import Optional

# 1. Завантаження налаштувань
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise ValueError("❌ Помилка: Немає ключів Supabase у .env. Перевір файл!")

supabase: Client = create_client(url, key)

app = FastAPI(title="FOP Assistant API 🇺🇦")

# 2. CORS (Дозволяємо фронтенду доступ)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ЛОГІКА НБУ ---
def get_nbu_rate(currency_code: str, date_val: date) -> float:
    """
    Отримує офіційний курс НБУ на дату.
    Повертає 0.0, якщо сталася помилка або курс не знайдено.
    """
    if currency_code == "UAH":
        return 1.0
        
    date_str = date_val.strftime("%Y%m%d") # Формат YYYYMMDD
    api_url = f"https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode={currency_code}&date={date_str}&json"
    
    try:
        response = requests.get(api_url, timeout=5)
        data = response.json()
        if not data:
            return 0.0
        return float(data[0]['rate'])
    except Exception as e:
        print(f"⚠️ НБУ Error: {e}")
        return 0.0

# --- МОДЕЛІ ДАНИХ ---
class TransactionCreate(BaseModel):
    user_id: str
    category_id: Optional[str] = None
    type: str # 'income' або 'expense'
    amount: float
    description: Optional[str] = None
    date: date
    currency: str = "UAH"
    manual_rate: Optional[float] = None

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"status": "active", "service": "FOP Assistant Backend"}

@app.post("/transactions")
def create_transaction(tx: TransactionCreate):
    """
    Створює транзакцію. Тягне курс НБУ, якщо не заданий вручну.
    """
    final_rate = 1.0
    amount_uah = tx.amount

    # Валютна магія
    if tx.currency != "UAH":
        if tx.manual_rate and tx.manual_rate > 0:
            final_rate = tx.manual_rate
        else:
            nbu_rate = get_nbu_rate(tx.currency, tx.date)
            if nbu_rate == 0:
                raise HTTPException(status_code=400, detail="НБУ не відповідає. Введіть курс вручну.")
            final_rate = nbu_rate
        
        amount_uah = tx.amount * final_rate

    # Підготовка даних для Supabase
    # Важливо: назви полів мають співпадати з базою даних!
    data_to_insert = {
        "user_id": tx.user_id,
        "category_id": tx.category_id,
        "transaction_type": tx.type,
        "transaction_amount": round(amount_uah, 2), # Гривня
        "transaction_date": tx.date.isoformat(),
        "notes": tx.description,
        "is_foreign_currency": tx.currency != "UAH",
        "currency_code": tx.currency,
        "amount_original": tx.amount if tx.currency != "UAH" else None,
        "exchange_rate": final_rate
    }

    try:
        response = supabase.table("transactions").insert(data_to_insert).execute()
        return {
            "message": "✅ Транзакцію успішно створено",
            "used_rate": final_rate,
            "amount_uah": round(amount_uah, 2),
            "db_response": response.data
        }
    except Exception as e:
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail=f"Помилка запису в базу: {str(e)}")