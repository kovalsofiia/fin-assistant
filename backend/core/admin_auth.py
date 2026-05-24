import os
from fastapi import Depends, HTTPException

from core.auth import get_current_user_id
from core.database import supabase


def _allowed_admin_emails() -> set[str]:
    raw = os.getenv("TAX_RULES_ADMIN_EMAILS", "").strip()
    if not raw:
        return set()
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def require_tax_rules_admin(current_user_id: str = Depends(get_current_user_id)) -> str:
    """
    Доступ до редагування tax_rules лише для email з TAX_RULES_ADMIN_EMAILS (через .env).
    Потрібен service_role ключ Supabase на бекенді для читання email користувача.
    """
    allowed = _allowed_admin_emails()
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="Редагування правил вимкнено: налаштуйте TAX_RULES_ADMIN_EMAILS у .env бекенду",
        )
    try:
        user_res = supabase.auth.admin.get_user_by_id(current_user_id)
        user = getattr(user_res, "user", None)
        email = (getattr(user, "email", None) or "").strip().lower()
        if email not in allowed:
            raise HTTPException(status_code=403, detail="Немає прав адміністратора податкових правил")
        return current_user_id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=403, detail="Не вдалося перевірити права адміністратора")
