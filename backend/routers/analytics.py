from fastapi import APIRouter, HTTPException
from core.database import supabase
from typing import Optional
from datetime import date as date_type, datetime, timedelta
import calendar

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/reports")
def get_reports(user_id: str, period: str = "monthly"):
    """
    Повертає загальні витрати та доходи згруповані за категоріями для вибраного періоду,
    а також підказки та прогнози поведінки.
    """
    try:
        query = supabase.table("transactions").select("transaction_amount, transaction_type, category_id, transaction_date").eq("user_id", user_id)
        
        today = datetime.now().date()
        if period == "monthly":
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
        income = 0
        categories_spent = {}
        
        for tx in transactions_data:
            amount = float(tx.get("transaction_amount", 0))
            is_expense = tx.get("transaction_type") == "expense"
            
            if is_expense:
                expenses += amount
                cat_id = tx.get("category_id")
                if cat_id:
                    categories_spent[cat_id] = categories_spent.get(cat_id, 0) + amount
            else:
                income += amount
                
        # Generate Tips & Forecast (behavior analysis)
        tips = []
        forecast = 0
        
        if period == "monthly":
            days_in_month = calendar.monthrange(today.year, today.month)[1]
            days_passed = today.day
            if days_passed > 0:
                avg_daily = expenses / days_passed
                forecast = avg_daily * days_in_month
                
            if forecast > income and income > 0:
                tips.append("⚠️ Прогнозовані витрати перевищують ваш поточний дохід за цей місяць. Рекомендуємо переглянути бюджет або зменшити щоденні витрати.")
            elif forecast > 0:
                tips.append(f"💡 При поточному темпі ви витратите близько {round(forecast, 2)} грн до кінця місяця.")

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
            "total_income": round(income, 2),
            "categories_spent": categories_spent,
            "forecast_expenses": round(forecast, 2),
            "tips": tips
        }
    except Exception as e:
        print(f"Error generating reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))
