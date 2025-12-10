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
    
@app.get("/transactions")
def get_transactions(
    user_id: str, 
    limit: int = 50, 
    offset: int = 0,             # Для пагінації (гортати сторінки)
    start_date: Optional[date] = None, # Фільтр: З якої дати
    end_date: Optional[date] = None,   # Фільтр: По яку дату
    type: Optional[str] = None         # Фільтр: 'income' або 'expense'
):
    """
    Отримує список транзакцій з можливістю фільтрації.
    
    Параметри:
    - start_date / end_date: Вибірка за період (напр. квартал).
    - type: Показати тільки доходи або витрати.
    - limit / offset: Пагінація.
    """
    try:
        # 1. Починаємо будувати запит
        query = supabase.table("transactions")\
            .select("*")\
            .eq("user_id", user_id)
            
        # 2. Накладаємо фільтри, якщо вони передані
        if start_date:
            query = query.gte("transaction_date", start_date.isoformat()) # >= start_date
            
        if end_date:
            query = query.lte("transaction_date", end_date.isoformat())   # <= end_date
            
        if type:
            query = query.eq("transaction_type", type)

        # 3. Сортування та ліміти (завжди в кінці)
        response = query\
            .order("transaction_date", desc=True)\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
            
        return response.data
        
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: str, user_id: str):
    """
    Видаляє транзакцію за її ID.
    Перевіряє, чи належить вона цьому користувачу.
    """
    try:
        # 1. Спочатку перевіряємо, чи існує такий запис у цього юзера
        # (Хоча RLS це робить, але краще мати явну перевірку для API відповіді)
        check = supabase.table("transactions")\
            .select("transaction_id")\
            .eq("transaction_id", transaction_id)\
            .eq("user_id", user_id)\
            .execute()
            
        if not check.data:
            raise HTTPException(status_code=404, detail="Транзакцію не знайдено або у вас немає прав на її видалення")

        # 2. Видаляємо
        supabase.table("transactions")\
            .delete()\
            .eq("transaction_id", transaction_id)\
            .eq("user_id", user_id)\
            .execute()
            
        return {"message": "✅ Транзакцію видалено"}
        
    except Exception as e:
        # Якщо це наша помилка 404 - прокидаємо її далі
        if isinstance(e, HTTPException):
            raise e
        print(f"Error deleting: {e}")
        raise HTTPException(status_code=500, detail=str(e))