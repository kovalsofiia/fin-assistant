from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from core.database import supabase

DEFAULT_ACCOUNTS: List[Dict[str, Any]] = [
    {
        "name": "Картка ФОП",
        "bank_name": None,
        "currency_code": "UAH",
        "is_business": True,
        "sort_order": 0,
    },
    {
        "name": "Особиста картка",
        "bank_name": None,
        "currency_code": "UAH",
        "is_business": False,
        "sort_order": 1,
    },
]


class AccountService:
    @staticmethod
    def list_accounts(user_id: str, include_inactive: bool = False) -> List[Dict]:
        query = supabase.table("accounts").select("*").eq("user_id", user_id)
        if not include_inactive:
            query = query.eq("is_active", True)
        response = query.order("sort_order").order("created_at").execute()
        rows = response.data or []
        if not rows:
            rows = AccountService.seed_default_accounts(user_id)
        return rows

    @staticmethod
    def seed_default_accounts(user_id: str) -> List[Dict]:
        payload = [{**item, "user_id": user_id, "is_active": True} for item in DEFAULT_ACCOUNTS]
        try:
            response = supabase.table("accounts").insert(payload).execute()
            return response.data or []
        except Exception as e:
            print(f"Seed default accounts failed for {user_id}: {e}")
            return []

    @staticmethod
    def get_account(user_id: str, account_id: str) -> Dict:
        response = (
            supabase.table("accounts")
            .select("*")
            .eq("id", account_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Рахунок не знайдено")
        return response.data[0]

    @staticmethod
    def resolve_is_fop(account: Optional[Dict], explicit_is_fop: bool) -> bool:
        if account is not None:
            return bool(account.get("is_business"))
        return explicit_is_fop
