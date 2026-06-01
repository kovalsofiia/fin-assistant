from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user_id
from models.kved import UserKvedsSync
from services.kved_validation_service import KvedValidationService, _load_restrictions_from_db

router = APIRouter(prefix="/kveds", tags=["KVED"])


@router.get("/restrictions")
def list_kved_restrictions(current_user_id: str = Depends(get_current_user_id)):
    """Довідник заборонених КВЕД (читання для автентифікованих)."""
    try:
        return _load_restrictions_from_db()
    except Exception as e:
        print(f"List kved restrictions: {e}")
        raise HTTPException(status_code=500, detail="Не вдалося завантажити довідник КВЕД")


@router.get("/me")
def get_my_kveds(current_user_id: str = Depends(get_current_user_id)):
    try:
        rows = KvedValidationService.load_user_kveds(current_user_id)
        return {"kveds": rows}
    except Exception as e:
        print(f"Get user kveds: {e}")
        if "user_kveds" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail="Таблиця user_kveds відсутня. Виконайте міграцію 002, 004 або 005_user_kveds_kved_code.sql",
            )
        if "kved_code" in str(e).lower() or "kved_name" in str(e).lower() or "42703" in str(e):
            raise HTTPException(
                status_code=400,
                detail="Схема user_kveds: kved_code, kved_name. Виконайте 005 та 006_user_kveds_columns.sql",
            )
        raise HTTPException(status_code=500, detail="Не вдалося завантажити КВЕД")


@router.put("/me")
def sync_my_kveds(
    payload: UserKvedsSync,
    current_user_id: str = Depends(get_current_user_id),
):
    try:
        items = [
            {
                "kved_code": k.resolved_kved_code(),
                "kved_name": k.resolved_kved_name(),
                "name": k.resolved_kved_name(),
            }
            for k in payload.kveds
            if k.resolved_kved_code()
        ]
        saved = KvedValidationService.sync_user_kveds(current_user_id, items)
        codes = [r["code"] for r in saved if r.get("code")]
        validation = KvedValidationService.validate_user_kveds(codes)
        return {"saved": saved, "validation": validation}
    except Exception as e:
        print(f"Sync user kveds: {e}")
        err = str(e)
        if "23503" in err or "kved_catalog" in err.lower():
            raise HTTPException(
                status_code=400,
                detail=(
                    "КВЕД відсутній у довіднику kved_catalog. "
                    "Перезапустіть backend і збережіть КВЕД ще раз."
                ),
            )
        if "user_kveds" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail="Таблиця user_kveds відсутня. Виконайте міграцію 002, 004 або 005_user_kveds_kved_code.sql",
            )
        if (
            "kved_code" in str(e).lower()
            or "kved_name" in str(e).lower()
            or "pgrst204" in str(e).lower()
        ):
            raise HTTPException(
                status_code=400,
                detail="Схема user_kveds: kved_code, kved_name. Виконайте 005 та 006_user_kveds_columns.sql",
            )
        raise HTTPException(status_code=500, detail="Не вдалося зберегти КВЕД")
