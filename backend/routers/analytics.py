from fastapi import APIRouter, HTTPException
from core.database import supabase
from typing import Optional
from datetime import date as date_type, datetime, timedelta
import calendar
from services.tax_service import TaxService
from models.setting import FopSettingsBase
from models.common import ReportingPeriod

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/reports")
def get_reports(user_id: str, period: str = "monthly", start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    Повертає загальні витрати та доходи згруповані за категоріями для вибраного періоду,
    а також підказки та прогнози поведінки.
    """
    try:
        query = supabase.table("transactions").select("transaction_amount, transaction_type, category_id, transaction_date, is_fop").eq("user_id", user_id)
        
        today = datetime.now().date()
        
        if start_date and end_date:
            query = query.gte("transaction_date", start_date).lte("transaction_date", end_date)
            # Determine effective period for tips logic
            try:
                sd = datetime.fromisoformat(start_date).date()
                ed = datetime.fromisoformat(end_date).date()
                delta = (ed - sd).days
                if delta > 25 and delta < 32:
                    period = "monthly"
            except:
                pass
        elif period == "monthly":
            first_day = today.replace(day=1)
            query = query.gte("transaction_date", first_day.isoformat())
        elif period == "weekly":
            first_day = today - timedelta(days=today.weekday())
            query = query.gte("transaction_date", first_day.isoformat())
        elif period == "yearly":
            first_day = today.replace(month=1, day=1)
            query = query.gte("transaction_date", first_day.isoformat())
        elif period == "daily":
            query = query.eq("transaction_date", today.isoformat())

        transactions_data = query.execute().data
        
        # Aggregate stats
        expenses = 0
        total_income = 0
        fop_income = 0
        categories_spent = {}
        
        for tx in transactions_data:
            amount = float(tx.get("transaction_amount", 0))
            is_expense = tx.get("transaction_type") == "expense"
            is_fop = tx.get("is_fop", True) if tx.get("is_fop") is not None else True
            
            if is_expense:
                expenses += amount
                cat_id = tx.get("category_id")
                if cat_id:
                    categories_spent[cat_id] = categories_spent.get(cat_id, 0) + amount
            else:
                total_income += amount
                if is_fop:
                    fop_income += amount
                
        # Generate Tips & Forecast (behavior analysis)
        tips = []
        forecast = 0
        
        if period == "monthly":
            days_in_month = calendar.monthrange(today.year, today.month)[1]
            days_passed = today.day
            if days_passed > 0:
                avg_daily = expenses / days_passed
                forecast = avg_daily * days_in_month
                
            if forecast > total_income and total_income > 0:
                tips.append(f"⚠️ **Увага**: Прогнозовані витрати ({round(forecast, 2)} грн) перевищують ваш поточний дохід ({round(total_income, 2)} грн). Рекомендуємо переглянути бюджет.")
            elif forecast > 0:
                tips.append(f"💡 **Прогноз**: При поточному темпі витрат, до кінця місяця ви витратите близько {round(forecast, 2)} грн.")
            
            if total_income > 0 and expenses > 0:
                savings_rate = ((total_income - expenses) / total_income) * 100
                if savings_rate > 20:
                    tips.append(f"👏 **Чудова робота**: Ваш загальний рівень заощаджень становить {round(savings_rate, 1)}%. Продовжуйте в тому ж дусі!")
                elif savings_rate < 5 and savings_rate > 0:
                    tips.append("🧐 **Порада**: Ваш рівень заощаджень досить низький. Спробуйте проаналізувати категорію з найбільшими витратами.")
            
            if total_income > 0:
                fop_ratio = (fop_income / total_income) * 100
                if fop_ratio > 80:
                    tips.append(f"💼 **Бізнес-активність**: {round(fop_ratio, 1)}% ваших доходів — це дохід ФОП. Не забувайте про ліміти!")
                elif fop_ratio < 20 and fop_income > 0:
                    tips.append(f"🏠 **Особисті доходи**: Більшість ваших надходжень ({round(100 - fop_ratio, 1)}%) є особистими та не підлягають оподаткуванню.")

            # Identify category with highest spent
            if categories_spent:
                top_cat_id = max(categories_spent, key=categories_spent.get)
                top_amount = categories_spent[top_cat_id]
                if top_amount > 0 and expenses > 0:
                    percent = (top_amount / expenses) * 100
                    if percent > 40:
                        tips.append(f"🔍 В одній з категорій витрачено {round(percent, 1)}% від загальної суми. Можливо, варто встановити для неї більш жорсткий ліміт.")

        return {
            "period": period,
            "total_expenses": round(expenses, 2),
            "total_income": round(total_income, 2),
            "fop_income": round(fop_income, 2),
            "personal_income": round(total_income - fop_income, 2),
            "categories_spent": categories_spent,
            "forecast_expenses": round(forecast, 2),
            "tips": tips
        }
    except Exception as e:
        print(f"Error generating reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/taxes")
def get_tax_history(user_id: str):
    """
    Отримує збережену історію податків.
    """
    try:
        res = supabase.table("tax_records").select("*").eq("user_id", user_id).order("year", desc=True).order("month", desc=True).execute()
        return res.data
    except Exception as e:
        print(f"Error fetching tax history for {user_id}: {e}")
        # If table doesn't exist, return empty list instead of 500
        if "relation \"tax_records\" does not exist" in str(e).lower():
            return []
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/history/taxes/sync")
def sync_tax_month(user_id: str, year: int, month: int):
    """
    Розраховує та зберігає показники податків за конкретний місяць.
    """
    try:
        # 1. Отримуємо налаштування ФОП
        settings_res = supabase.table("fop_settings").select("*").eq("user_id", user_id).execute()
        if not settings_res.data:
            raise HTTPException(status_code=404, detail="Налаштування ФОП не знайдено")
        
        settings = FopSettingsBase(**settings_res.data[0])
        
        # 2. Розраховуємо дохід ФОП за цей місяць
        start_date = date_type(year, month, 1).isoformat()
        last_day = calendar.monthrange(year, month)[1]
        end_date = date_type(year, month, last_day).isoformat()
        
        tx_res = supabase.table("transactions")\
            .select("transaction_amount")\
            .eq("user_id", user_id)\
            .eq("transaction_type", "income")\
            .eq("is_fop", True)\
            .gte("transaction_date", start_date)\
            .lte("transaction_date", end_date)\
            .execute()
        
        fop_income = sum(float(tx["transaction_amount"]) for tx in tx_res.data)
        
        # 3. Розраховуємо податки через TaxService
        calc_date = date_type(year, month, 1) # Базова дата місяця
        taxes = TaxService.calculate_taxes(user_id, settings, fop_income, ReportingPeriod.MONTH, calc_date)
        
        # 4. Зберігаємо/Оновлюємо запис
        record_data = {
            "user_id": user_id,
            "year": year,
            "month": month,
            "fop_income": round(fop_income, 2),
            "esv": taxes["esv"],
            "income_tax": taxes["single_tax"],
            "military_tax": taxes["military_tax"]
        }
        
        # Перевіряємо чи вже є запис
        existing = supabase.table("tax_records")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("year", year)\
            .eq("month", month)\
            .execute()
            
        if existing.data:
            res = supabase.table("tax_records").update(record_data).eq("id", existing.data[0]["id"]).execute()
        else:
            res = supabase.table("tax_records").insert(record_data).execute()
            
        return res.data[0]
        
    except Exception as e:
        print(f"Error syncing tax month for {user_id}: {e}")
        if "relation \"tax_records\" does not exist" in str(e).lower():
            raise HTTPException(status_code=400, detail="Таблиця 'tax_records' відсутня. Будь ласка, виконайте SQL міграцію.")
        if "column \"registration_date\" does not exist" in str(e).lower():
             # Fallback logic for TaxService calculation if registration_date missing
             # We already handled this in tax_service.py by checking if it's truthy
             pass
        raise HTTPException(status_code=500, detail=f"Помилка синхронізації: {str(e)}")
@router.post("/history/taxes/sync_all")
def sync_all_taxes(user_id: str):
    """
    Знаходить усі місяці, в яких були транзакції, та синхронізує їх в історію податків.
    Оптимізовано (Smart Sync): перераховує лише за зміни даних або для поточного місяця.
    """
    try:
        today = datetime.now().date()
        
        # 1. Отримуємо налаштування ФОП
        settings_res = supabase.table("fop_settings").select("*").eq("user_id", user_id).execute()
        if not settings_res.data:
            raise HTTPException(status_code=404, detail="Налаштування ФОП не знайдено")
        
        settings = FopSettingsBase(**settings_res.data[0])
        
        # 2. Отримуємо всі існуючі записи про податки (для порівняння)
        existing_records_res = supabase.table("tax_records").select("*").eq("user_id", user_id).execute()
        existing_map = {(r["year"], r["month"]): r for r in existing_records_res.data}
        
        # 3. Отримуємо всі доходи для розрахунку поточних сум по місяцях
        tx_res = supabase.table("transactions")\
            .select("transaction_amount, transaction_date")\
            .eq("user_id", user_id)\
            .eq("transaction_type", "income")\
            .eq("is_fop", True)\
            .execute()
        
        if not tx_res.data:
            return {"message": "Транзакцій не знайдено", "synced_count": 0}
            
        income_by_period = {}
        for tx in tx_res.data:
            dt = datetime.fromisoformat(tx["transaction_date"])
            period = (dt.year, dt.month)
            income_by_period[period] = income_by_period.get(period, 0) + float(tx["transaction_amount"])
            
        synced_count = 0
        skipped_count = 0
        results = []
        
        # 4. Проходимо по кожному періоду, де є дохід
        for (year, month), current_fop_income in sorted(income_by_period.items()):
            existing = existing_map.get((year, month))
            is_current_month = (year == today.year and month == today.month)
            
            # Smart Sync Check:
            # Якщо запис є, він не за поточний місяць і сума доходу не змінилася — пропускаємо перерахунок
            if existing and not is_current_month:
                stored_income = float(existing.get("fop_income", 0))
                if abs(stored_income - current_fop_income) < 0.01:
                    skipped_count += 1
                    continue
            
            # Розраховуємо податки через TaxService
            calc_date = date_type(year, month, 1)
            taxes = TaxService.calculate_taxes(user_id, settings, current_fop_income, ReportingPeriod.MONTH, calc_date)
            
            record_data = {
                "user_id": user_id,
                "year": year,
                "month": month,
                "fop_income": round(current_fop_income, 2),
                "esv": taxes["esv"],
                "income_tax": taxes["single_tax"],
                "military_tax": taxes["military_tax"]
            }
            
            if existing:
                res = supabase.table("tax_records").update(record_data).eq("id", existing["id"]).execute()
            else:
                res = supabase.table("tax_records").insert(record_data).execute()
            
            synced_count += 1
            if res.data:
                results.append(res.data[0])
                
        return {
            "message": f"Синхронізовано: {synced_count}, Пропущено (без змін): {skipped_count}",
            "synced_count": synced_count,
            "skipped_count": skipped_count,
            "records": results
        }
        
    except Exception as e:
        print(f"Error syncing all taxes for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
