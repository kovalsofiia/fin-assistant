from typing import Optional
from fastapi import APIRouter, HTTPException
from core.database import supabase
from services.nbu_service import get_nbu_rate
from models.transaction import TransactionCreate, TransactionPatch  
from datetime import date as date_type

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.post("/")
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
    
@router.get("/")
def get_transactions(
    user_id: str, 
    limit: int = 50, 
    offset: int = 0,             # Для пагінації (гортати сторінки)
    start_date: Optional[date_type] = None, # Фільтр: З якої дати
    end_date: Optional[date_type] = None,   # Фільтр: По яку дату
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
    
@router.delete("/{transaction_id}")
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
    
@router.patch("/{transaction_id}")
def patch_transaction(transaction_id: str, user_id: str, patch: TransactionPatch):
    """
    Часткове оновлення транзакції.
    Змінює тільки передані поля.
    Якщо змінено суму, валюту або дату — автоматично перераховує курс і гривневий еквівалент.
    """
    try:
        # 1. Отримуємо поточну версію транзакції з бази
        existing_response = supabase.table("transactions")\
            .select("*")\
            .eq("transaction_id", transaction_id)\
            .eq("user_id", user_id)\
            .execute()
            
        if not existing_response.data:
            raise HTTPException(status_code=404, detail="Транзакцію не знайдено")

        old_data = existing_response.data[0]

        # 2. Визначаємо нові значення (або беремо старі, якщо нові не передані)
        # Це логіка злиття (Merge)
        new_amount = patch.amount if patch.amount is not None else old_data['amount_original'] or old_data['transaction_amount']
        new_date = patch.date if patch.date is not None else date_type.fromisoformat(old_data['transaction_date'])
        new_currency = patch.currency if patch.currency is not None else old_data['currency_code']
        # Якщо передали manual_rate, беремо його, інакше - None (щоб спрацювала логіка НБУ або старий курс)
        new_manual_rate = patch.manual_rate 

        # 3. Перевіряємо, чи треба перераховувати фінанси
        # Перерахунок потрібен, якщо змінилося хоч одне з фінансових полів
        needs_recalc = (
            (patch.amount is not None) or 
            (patch.date is not None) or 
            (patch.currency is not None) or
            (patch.manual_rate is not None)
        )

        final_amount_uah = old_data['transaction_amount']
        final_rate = old_data['exchange_rate']
        final_amount_original = old_data['amount_original']

        if needs_recalc:
            # Логіка розрахунку (така ж як в create)
            if new_currency != "UAH":
                if new_manual_rate and new_manual_rate > 0:
                    final_rate = new_manual_rate
                else:
                    # Якщо валюта/дата змінилась, а курс вручну не дали - питаємо НБУ
                    # АЛЕ: Якщо дата і валюта НЕ змінились, а змінилась тільки сума - можна залишити старий курс?
                    # Для надійності краще завжди тягнути актуальний курс НБУ на цю дату.
                    nbu_rate = get_nbu_rate(new_currency, new_date)
                    if nbu_rate == 0:
                         raise HTTPException(status_code=400, detail="Не вдалося отримати курс НБУ для перерахунку.")
                    final_rate = nbu_rate
                
                final_amount_uah = new_amount * final_rate
                final_amount_original = new_amount
            else:
                # Якщо стала гривня
                final_amount_uah = new_amount
                final_rate = 1.0
                final_amount_original = None

        # 4. Формуємо об'єкт для оновлення
        data_to_update = {}
        
        # Оновлюємо тільки ті поля, що передали + перераховані фінанси
        if patch.category_id is not None: data_to_update["category_id"] = patch.category_id
        if patch.type is not None: data_to_update["transaction_type"] = patch.type
        if patch.description is not None: data_to_update["notes"] = patch.description
        
        # Якщо був перерахунок, пишемо нові цифри
        if needs_recalc:
            data_to_update["transaction_amount"] = round(final_amount_uah, 2)
            data_to_update["transaction_date"] = new_date.isoformat()
            data_to_update["is_foreign_currency"] = new_currency != "UAH"
            data_to_update["currency_code"] = new_currency
            data_to_update["amount_original"] = final_amount_original
            data_to_update["exchange_rate"] = final_rate

        # 5. Зберігаємо в базу
        response = supabase.table("transactions")\
            .update(data_to_update)\
            .eq("transaction_id", transaction_id)\
            .eq("user_id", user_id)\
            .execute()
            
        return {
            "message": "✅ Транзакцію оновлено (PATCH)",
            "changes": data_to_update,
            "full_data": response.data
        }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"PATCH error: {e}")
        raise HTTPException(status_code=500, detail=str(e))