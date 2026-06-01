from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user_id
from core.database import supabase
from models.account import AccountCreate, AccountUpdate
from services.account_service import AccountService

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("/")
def list_accounts(
    include_inactive: bool = False,
    current_user_id: str = Depends(get_current_user_id),
):
    """Список рахунків користувача; при відсутності — створюються типові ФОП + особистий."""
    try:
        return AccountService.list_accounts(current_user_id, include_inactive=include_inactive)
    except Exception as e:
        print(f"List accounts error: {e}")
        if "relation \"accounts\" does not exist" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail="Таблиця accounts відсутня. Виконайте міграцію backend/migrations/001_add_accounts.sql у Supabase.",
            )
        raise HTTPException(status_code=500, detail="Не вдалося завантажити рахунки")


@router.post("/")
def create_account(
    payload: AccountCreate,
    current_user_id: str = Depends(get_current_user_id),
):
    try:
        data = {
            "user_id": current_user_id,
            "name": payload.name,
            "bank_name": payload.bank_name,
            "currency_code": payload.currency_code,
            "is_business": payload.is_business,
            "is_active": True,
            "sort_order": payload.sort_order,
        }
        response = supabase.table("accounts").insert(data).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Не вдалося створити рахунок")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create account error: {e}")
        raise HTTPException(status_code=500, detail="Не вдалося створити рахунок")


@router.patch("/{account_id}")
def update_account(
    account_id: str,
    payload: AccountUpdate,
    current_user_id: str = Depends(get_current_user_id),
):
    AccountService.get_account(current_user_id, account_id)
    patch_fields = payload.dict(exclude_unset=True)
    if not patch_fields:
        raise HTTPException(status_code=400, detail="Немає полів для оновлення")
    try:
        response = (
            supabase.table("accounts")
            .update(patch_fields)
            .eq("id", account_id)
            .eq("user_id", current_user_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=500, detail="Не вдалося оновити рахунок")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update account error: {e}")
        raise HTTPException(status_code=500, detail="Не вдалося оновити рахунок")


@router.delete("/{account_id}")
def delete_account(
    account_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    AccountService.get_account(current_user_id, account_id)
    try:
        supabase.table("transactions").update({"account_id": None}).eq(
            "account_id", account_id
        ).eq("user_id", current_user_id).execute()

        supabase.table("accounts").delete().eq("id", account_id).eq(
            "user_id", current_user_id
        ).execute()
        return {"message": "Рахунок видалено; транзакції залишено без прив’язки до рахунку"}
    except Exception as e:
        print(f"Delete account error: {e}")
        raise HTTPException(status_code=500, detail="Не вдалося видалити рахунок")
