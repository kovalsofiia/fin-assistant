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

@router.get("/summary")
def get_transaction_summary(
    user_id: str,
    end_date: Optional[date_type] = None
):
    """
    Повертає агреговану статистику (дохід, витрати, баланс).
    Якщо передати end_date, рахує все від початку часів до цієї дати.
    """
    try:
        # Використовуємо rpc або просто витягуємо суми через select
        # Для простоти на Supabase Python SDK ми можемо додати .sum() 
        # але нативне SDK не завжди це підтримує зручно без RPC.
        # Тому просто витягнемо необхідні поля і просумуємо.
        # (У реальному проекті краще мати RPC функцію в Postgres).
        
        query = supabase.table("transactions")\
            .select("transaction_amount, transaction_type, transaction_date")\
            .eq("user_id", user_id)
        
        if end_date:
            query = query.lte("transaction_date", end_date.isoformat())

        response = query.execute()
        
        income = 0.0
        expense = 0.0
        months = set()
        
        for tx in response.data:
            amount = float(tx["transaction_amount"])
            date_str = tx.get("transaction_date", "")
            if date_str:
                months.add(date_str[:7])

            if tx["transaction_type"] == "income":
                income += amount
            else:
                expense += amount
        
        return {
            "totalIncome": round(income, 2),
            "totalExpense": round(expense, 2),
            "balance": round(income - expense, 2),
            "monthsCount": len(months)
        }
    except Exception as e:
        print(f"Summary Error: {e}")
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
        # Отримуємо тільки ті поля, які були реально в JSON запиті
        patch_fields = patch.dict(exclude_unset=True)
        
        new_amount = patch.amount if patch.amount is not None else old_data['amount_original'] or old_data['transaction_amount']
        new_date = patch.date if patch.date is not None else date_type.fromisoformat(old_data['transaction_date'])
        new_currency = patch.currency if patch.currency is not None else old_data['currency_code']
        # manual_rate сюди потрапить тільки якщо він був у patch_fields
        provided_manual_rate = patch_fields.get('manual_rate')

        # 3. Перевіряємо, чи треба перераховувати фінанси
        needs_recalc = any(f in patch_fields for f in ['amount', 'date', 'currency', 'manual_rate'])

        final_amount_uah = old_data['transaction_amount']
        final_rate = old_data['exchange_rate']
        final_amount_original = old_data['amount_original']
        
        if needs_recalc:
            if new_currency != "UAH":
                # 1. Якщо користувач передав курс і він > 0 — використовуємо його
                if provided_manual_rate and provided_manual_rate > 0:
                    final_rate = provided_manual_rate
                
                # 2. Якщо користувач ЯВНО передав порожній курс (null або 0) — тягнемо НБУ
                # або якщо змінилась валюта чи дата — також тягнемо НБУ
                elif ('manual_rate' in patch_fields and not provided_manual_rate) or \
                     new_currency != old_data['currency_code'] or \
                     new_date.isoformat() != old_data['transaction_date']:
                    
                    nbu_rate = get_nbu_rate(new_currency, new_date)
                    if nbu_rate == 0:
                         raise HTTPException(status_code=400, detail="НБУ не відповідає. Введіть курс вручну.")
                    final_rate = nbu_rate
                
                # 3. В іншому випадку (наприклад, змінили тільки опис або суму без зміни курсу/дати) 
                # — залишаємо старий курс
                else:
                    final_rate = old_data['exchange_rate']
                
                final_amount_uah = new_amount * final_rate
                final_amount_original = new_amount

            else:
                # Якщо стала гривня (або була гривня)
                # Ця частина у вас ідеальна — ми зачищаємо валютні "хвости"
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