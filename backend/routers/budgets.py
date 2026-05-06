from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from core.database import supabase
from core.auth import get_current_user_id
from models.budget import BudgetCreate, BudgetUpdate
from datetime import date as date_type, datetime
import calendar

router = APIRouter(prefix="/budgets", tags=["Budgets"])

@router.post("/")
def create_budget(budget: BudgetCreate, current_user_id: str = Depends(get_current_user_id)):
    """
    Створює новий ліміт/бюджет.
    """
    data_to_insert = {
        "user_id": current_user_id,
        "category_id": budget.category_id,
        "amount": round(budget.amount, 2),
        "period": budget.period.value,
        "start_date": budget.start_date.isoformat() if budget.start_date else None,
        "end_date": budget.end_date.isoformat() if budget.end_date else None
    }

    try:
        response = supabase.table("budgets").insert(data_to_insert).execute()
        return {
            "message": "Бюджет успішно створено",
            "budget": response.data[0] if response.data else None
        }
    except Exception as e:
        print(f"DB Error creating budget: {e}")
        raise HTTPException(status_code=500, detail=f"Помилка створення бюджету: {str(e)}")


@router.get("/")
def get_budgets(current_user_id: str = Depends(get_current_user_id)):
    """
    Отримує всі бюджети користувача.
    """
    try:
        response = supabase.table("budgets")\
            .select("*")\
            .eq("user_id", current_user_id)\
            .order("created_at", desc=True)\
            .execute()
            
        return response.data
    except Exception as e:
        print(f"Error fetching budgets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{budget_id}")
def update_budget(
    budget_id: str,
    patch: BudgetUpdate,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Оновлює бюджет (суму, категорію, період).
    """
    try:
        data_to_update = {}
        patch_dict = patch.dict(exclude_unset=True)
        
        if "category_id" in patch_dict: data_to_update["category_id"] = patch_dict["category_id"]
        if "amount" in patch_dict: data_to_update["amount"] = round(patch_dict["amount"], 2)
        if "period" in patch_dict: data_to_update["period"] = patch_dict["period"].value
        if "start_date" in patch_dict: 
            data_to_update["start_date"] = patch_dict["start_date"].isoformat() if patch_dict["start_date"] else None
        if "end_date" in patch_dict: 
            data_to_update["end_date"] = patch_dict["end_date"].isoformat() if patch_dict["end_date"] else None

        if not data_to_update:
             return {"message": "Немає даних для оновлення"}

        response = supabase.table("budgets")\
            .update(data_to_update)\
            .eq("id", budget_id)\
            .eq("user_id", current_user_id)\
            .execute()
            
        return {
            "message": "Бюджет оновлено",
            "full_data": response.data
        }
    except Exception as e:
        print(f"PATCH error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{budget_id}")
def delete_budget(budget_id: str, current_user_id: str = Depends(get_current_user_id)):
    """
    Видаляє бюджет за його ID.
    """
    try:
        check = supabase.table("budgets")\
            .select("id")\
            .eq("id", budget_id)\
            .eq("user_id", current_user_id)\
            .execute()
            
        if not check.data:
            raise HTTPException(status_code=404, detail="Бюджет не знайдено або у вас немає прав на його видалення")

        supabase.table("budgets")\
            .delete()\
            .eq("id", budget_id)\
            .eq("user_id", current_user_id)\
            .execute()
            
        return {"message": "Бюджет видалено"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"Error deleting budget: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_month_boundaries(date_obj: date_type):
    first_day = date_obj.replace(day=1)
    last_day = date_obj.replace(day=calendar.monthrange(date_obj.year, date_obj.month)[1])
    return first_day.isoformat(), last_day.isoformat()


@router.get("/progress")
def get_budgets_progress(current_user_id: str = Depends(get_current_user_id)):
    """
    Повертає бюджети користувача разом із поточними витратами (spent) 
    по кожному бюджету для відповідного періоду (зараз підтримується 'monthly').
    """
    try:
        # 1. Fetch budgets
        budgets_resp = supabase.table("budgets").select("*").eq("user_id", current_user_id).execute()
        budgets = budgets_resp.data

        if not budgets:
            return []

        # We will only look at "monthly" boundaries for now for simplicity, 
        # or implement logic to calculate boundaries per budget period
        today = datetime.now().date()
        first_day, last_day = get_month_boundaries(today)

        # 2. Fetch expenses for the user in this month
        # Since budgets apply only to expenses, filter by transaction_type = expense
        tx_resp = supabase.table("transactions")\
            .select("category_id, transaction_amount")\
            .eq("user_id", current_user_id)\
            .eq("transaction_type", "expense")\
            .gte("transaction_date", first_day)\
            .lte("transaction_date", last_day)\
            .execute()
        
        transactions = tx_resp.data

        # 3. Calculate spent per category and total
        spent_by_category = {}
        total_monthly_spent = 0.0

        for tx in transactions:
            amount = float(tx.get("transaction_amount", 0))
            cat_id = tx.get("category_id")
            
            total_monthly_spent += amount
            if cat_id:
                spent_by_category[cat_id] = spent_by_category.get(cat_id, 0) + amount

        # 4. Map spent amounts to budgets
        budget_progress = []
        for b in budgets:
            spent = 0.0
            
            if b.get("period") != "monthly":
                # For custom/weekly budgets, one would calculate the respective bounds.
                # Assuming 'monthly' for the main logic for now to show concept:
                pass 
                
            cat_id = b.get("category_id")
            if cat_id:
                # Specific category budget
                spent = spent_by_category.get(cat_id, 0.0)
            else:
                # Overall budget
                spent = total_monthly_spent

            budget_progress.append({
                **b,
                "spent": round(spent, 2)
            })

        return budget_progress

    except Exception as e:
        print(f"Error fetching progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))
