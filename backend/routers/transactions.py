from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from core.database import supabase
from core.auth import get_current_user_id
from services.nbu_service import get_nbu_rate
from models.transaction import TransactionCreate, TransactionPatch
from models.common import FopGroup
from models.setting import FopSettingsBase
from services.account_service import AccountService
from datetime import date as date_type

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def _get_user_fop_settings(user_id: str) -> Optional[FopSettingsBase]:
    profile_res = supabase.table("profiles").select("is_fop").eq("id", user_id).execute()
    if not profile_res.data:
        return None
    if not profile_res.data[0].get("is_fop", False):
        return None

    settings_res = supabase.table("fop_settings").select("*").eq("user_id", user_id).execute()
    if not settings_res.data:
        return None
    return FopSettingsBase(**settings_res.data[0])


def _validate_fx_transaction_rules(
    user_id: str,
    currency: str,
    *,
    applies_to_fop_rules: bool = True,
):
    if currency == "UAH":
        return
    if not applies_to_fop_rules:
        return

    settings = _get_user_fop_settings(user_id)
    if not settings:
        return

    if settings.fop_group in [FopGroup.GROUP_1, FopGroup.GROUP_4]:
        raise HTTPException(
            status_code=400,
            detail="Валютні операції заборонені для ФОП 1 та 4 групи.",
        )

    if settings.is_zed is False:
        raise HTTPException(
            status_code=400,
            detail="Валютні операції потребують увімкненого режиму ЗЕД у налаштуваннях ФОП.",
        )


def _category_ids_for_search(user_id: str, search_value: str) -> List[str]:
    cat_res = (
        supabase.table("categories")
        .select("id")
        .or_(f"user_id.is.null,user_id.eq.{user_id}")
        .ilike("name", f"%{search_value}%")
        .execute()
    )
    return [str(row.get("id")) for row in (cat_res.data or []) if row.get("id")]

@router.post("/")
def create_transaction(tx: TransactionCreate, current_user_id: str = Depends(get_current_user_id)):
    """
    Створює транзакцію. Тягне курс НБУ, якщо не заданий вручну.
    """
    final_rate = 1.0
    amount_uah = tx.amount

    account = None
    if tx.account_id:
        account = AccountService.get_account(current_user_id, str(tx.account_id))

    resolved_is_fop = AccountService.resolve_is_fop(account, tx.is_fop)
    _validate_fx_transaction_rules(
        current_user_id,
        tx.currency,
        applies_to_fop_rules=resolved_is_fop,
    )

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
        "user_id": current_user_id,
        "category_id": tx.category_id,
        "transaction_type": tx.type,
        "transaction_amount": round(amount_uah, 2), # Гривня
        "transaction_date": tx.date.isoformat(),
        "notes": tx.description,
        "is_foreign_currency": tx.currency != "UAH",
        "currency_code": tx.currency,
        "amount_original": tx.amount if tx.currency != "UAH" else None,
        "exchange_rate": final_rate,
        "is_fop": resolved_is_fop,
        "account_id": str(tx.account_id) if tx.account_id else None,
    }

    try:
        response = supabase.table("transactions").insert(data_to_insert).execute()
        return {
            "message": "Транзакцію успішно створено",
            "used_rate": final_rate,
            "amount_uah": round(amount_uah, 2),
            "db_response": response.data
        }
    except Exception as e:
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail=f"Помилка запису в базу: {str(e)}")
    
@router.get("/")
def get_transactions(
    current_user_id: str = Depends(get_current_user_id),
    limit: int = 50, 
    offset: int = 0,             # Для пагінації (гортати сторінки)
    start_date: Optional[date_type] = None, # Фільтр: З якої дати
    end_date: Optional[date_type] = None,   # Фільтр: По яку дату
    type: Optional[str] = None,        # Фільтр: 'income' або 'expense'
    category_id: Optional[str] = None,  # Фільтр: за категорією
    account_id: Optional[str] = None,
    search: Optional[str] = None,
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
            .eq("user_id", current_user_id)
            
        # 2. Накладаємо фільтри, якщо вони передані
        if start_date:
            query = query.gte("transaction_date", start_date.isoformat()) # >= start_date
            
        if end_date:
            query = query.lte("transaction_date", end_date.isoformat())   # <= end_date
            
        if type:
            query = query.eq("transaction_type", type)
            
        if category_id:
            query = query.eq("category_id", category_id)

        if account_id:
            query = query.eq("account_id", account_id)

        if search:
            search_value = search.strip()
            if search_value:
                escaped = search_value.replace("%", "").replace(",", " ")
                or_filters = [
                    f"notes.ilike.%{escaped}%",
                    f"currency_code.ilike.%{escaped}%",
                    f"transaction_type.ilike.%{escaped}%",
                ]

                # Match by exact date if user entered ISO date fragment.
                if len(escaped) >= 4 and escaped[0:4].isdigit():
                    or_filters.append(f"transaction_date.ilike.%{escaped}%")

                # Match numeric search against amount fields (exact rounded value).
                try:
                    numeric_value = float(escaped.replace(" ", ""))
                    numeric_rounded = round(numeric_value, 2)
                    or_filters.append(f"transaction_amount.eq.{numeric_rounded}")
                    or_filters.append(f"amount_original.eq.{numeric_rounded}")
                except Exception:
                    pass

                category_ids = _category_ids_for_search(current_user_id, escaped)
                if category_ids:
                    joined_ids = ",".join(category_ids)
                    or_filters.append(f"category_id.in.({joined_ids})")

                query = query.or_(",".join(or_filters))

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
    current_user_id: str = Depends(get_current_user_id),
    end_date: Optional[date_type] = None
):
    """
    Повертає агреговану статистику (дохід, витрати, баланс).
    Якщо передати end_date, рахує все від початку часів до цієї дати.
    """
    try:
        query = supabase.table("transactions")\
            .select("transaction_amount, transaction_type, transaction_date, is_fop")\
            .eq("user_id", current_user_id)
        
        if end_date:
            query = query.lte("transaction_date", end_date.isoformat())

        response = query.execute()
        
        income = 0.0
        fop_income = 0.0
        expense = 0.0
        months = set()
        transaction_dates = []
        
        for tx in response.data:
            amount = float(tx["transaction_amount"])
            date_str = tx.get("transaction_date", "")
            is_fop = tx.get("is_fop", True) if tx.get("is_fop") is not None else True
            
            if date_str:
                months.add(date_str[:7])
                transaction_dates.append(date_str)

            if tx["transaction_type"] == "income":
                income += amount
                if is_fop:
                    fop_income += amount
            else:
                expense += amount
        
        first_date = min(transaction_dates) if transaction_dates else None
        last_date = max(transaction_dates) if transaction_dates else None

        return {
            "totalIncome": round(income, 2),
            "totalFopIncome": round(fop_income, 2),
            "totalExpense": round(expense, 2),
            "balance": round(income - expense, 2),
            "balanceFop": round(fop_income - expense, 2),
            "monthsCount": len(months),
            "firstDate": first_date,
            "lastDate": last_date
        }
    except Exception as e:
        print(f"Summary Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: str, current_user_id: str = Depends(get_current_user_id)):
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
            .eq("user_id", current_user_id)\
            .execute()
            
        if not check.data:
            raise HTTPException(status_code=404, detail="Транзакцію не знайдено або у вас немає прав на її видалення")

        # 2. Видаляємо
        supabase.table("transactions")\
            .delete()\
            .eq("transaction_id", transaction_id)\
            .eq("user_id", current_user_id)\
            .execute()
            
        return {"message": "Транзакцію видалено"}
        
    except Exception as e:
        # Якщо це наша помилка 404 - прокидаємо її далі
        if isinstance(e, HTTPException):
            raise e
        print(f"Error deleting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{transaction_id}")
def patch_transaction(
    transaction_id: str,
    patch: TransactionPatch,
    current_user_id: str = Depends(get_current_user_id),
):
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
            .eq("user_id", current_user_id)\
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

        patch_account = None
        effective_account_id = old_data.get("account_id")
        if "account_id" in patch_fields:
            raw_account_id = patch_fields.get("account_id")
            effective_account_id = str(raw_account_id) if raw_account_id else None
        if effective_account_id:
            patch_account = AccountService.get_account(current_user_id, effective_account_id)

        explicit_is_fop = (
            patch.is_fop
            if patch.is_fop is not None
            else (old_data.get("is_fop", True) if old_data.get("is_fop") is not None else True)
        )
        resolved_is_fop = AccountService.resolve_is_fop(patch_account, explicit_is_fop)

        # 3. Перевіряємо, чи треба перераховувати фінанси
        needs_recalc = any(f in patch_fields for f in ['amount', 'date', 'currency', 'manual_rate'])

        final_amount_uah = old_data['transaction_amount']
        final_rate = old_data['exchange_rate']
        final_amount_original = old_data['amount_original']
        
        if needs_recalc:
            _validate_fx_transaction_rules(
                current_user_id,
                new_currency,
                applies_to_fop_rules=resolved_is_fop,
            )
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

        if patch.is_fop is not None or patch_account is not None:
            data_to_update["is_fop"] = resolved_is_fop
        if "account_id" in patch_fields:
            data_to_update["account_id"] = effective_account_id

        # 5. Зберігаємо в базу
        response = supabase.table("transactions")\
            .update(data_to_update)\
            .eq("transaction_id", transaction_id)\
            .eq("user_id", current_user_id)\
            .execute()
            
        return {
            "message": "Транзакцію оновлено (PATCH)",
            "changes": data_to_update,
            "full_data": response.data
        }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"PATCH error: {e}")
        raise HTTPException(status_code=500, detail=str(e))