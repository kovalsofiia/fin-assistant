from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from core.database import supabase
from core.auth import get_current_user_id
from models.setting import FopSettingsUpdate
from models.common import FopGroup, TaxSystem, ActivityType, ReportingPeriod
from core.constants import DEFAULT_G3_RATE, DEFAULT_MILITARY_RATE, MIN_ESV

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/{user_id}")
def get_fop_settings(user_id: str, current_user_id: str = Depends(get_current_user_id)):
    """
    Отримати податкові налаштування користувача (група, ставки, ЗЕД).
    """
    try:
        if user_id != current_user_id:
            raise HTTPException(status_code=403, detail="Доступ заборонено")
        response = supabase.table("fop_settings").select("*").eq("user_id", user_id).execute()
        
        if not response.data:
            default_data = {
                "user_id": user_id,
                "fop_group": FopGroup.GROUP_3,
                "income_tax_percent": DEFAULT_G3_RATE,
                "military_tax_percent": DEFAULT_MILITARY_RATE,
                "esv_value": MIN_ESV,
                "is_zed": False,
                "tax_system": TaxSystem.SIMPLIFIED,
                "activity_type": ActivityType.SERVICES,
                "reporting_period": ReportingPeriod.QUARTER,
                "has_employees": False,
                "employees_count": 0,
                "is_vat_payer": False,
                "registration_date": None,
                "esv_covered_by_primary_employment": False
            }
            try:
                new_settings = supabase.table("fop_settings").insert(default_data).execute()
                return new_settings.data[0]
            except Exception as e:
                print(f"Failed to create default settings for {user_id}: {e}")
                # return default_data even if insert fails, so UI doesn't crash
                return default_data
            
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"Error getting settings for {user_id}: {e}")
        # Return sensible defaults if the query fails (likely due to schema mismatch)
        return {
            "user_id": user_id,
            "fop_group": FopGroup.GROUP_3,
            "income_tax_percent": DEFAULT_G3_RATE,
            "military_tax_percent": DEFAULT_MILITARY_RATE,
            "esv_value": MIN_ESV,
            "is_zed": False,
            "tax_system": TaxSystem.SIMPLIFIED,
            "activity_type": ActivityType.SERVICES,
            "registration_date": None,
            "esv_covered_by_primary_employment": False
        }

@router.patch("/{user_id}")
def update_fop_settings(
    user_id: str,
    settings: FopSettingsUpdate,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Оновити налаштування з високою стійкістю до помилок схеми.
    """
    try:
        if user_id != current_user_id:
            raise HTTPException(status_code=403, detail="Доступ заборонено")
        update_data = jsonable_encoder(settings.dict(exclude_unset=True))
        if not update_data:
            raise HTTPException(status_code=400, detail="Немає даних для оновлення")
            
        try:
            response = supabase.table("fop_settings").update(update_data).eq("user_id", user_id).execute()
            if not response.data:
                # Якщо запису немає, створимо його (upsert)
                update_data["user_id"] = user_id
                response = supabase.table("fop_settings").upsert(update_data).execute()
            return response.data[0]
        except Exception as db_error:
            error_str = str(db_error).lower()
            # Якщо проблема в конкретній колонці, якої немає в БД
            if "column" in error_str and "does not exist" in error_str:
                # Спробуємо видалити проблемні нові поля і зберегти що залишилось
                new_fields = ["registration_date", "tax_system", "activity_type", "has_employees", "employees_count", "is_vat_payer", "land_area_ha", "normative_land_value", "esv_covered_by_primary_employment"]
                for field in new_fields:
                    if field in update_data:
                        del update_data[field]
                
                # Друга спроба (upsert гарантує створення запису, якщо його нема)
                update_data["user_id"] = user_id
                response = supabase.table("fop_settings").upsert(update_data).execute()
                if response.data:
                    return response.data[0]
                raise HTTPException(status_code=500, detail="Не вдалося оновити навіть базові поля")
            raise db_error
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"Settings Update Error for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Помилка оновлення: {str(e)}")