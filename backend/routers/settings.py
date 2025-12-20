from fastapi import APIRouter, HTTPException
from core.database import supabase
from models.setting import FopSettingsUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/{user_id}")
def get_fop_settings(user_id: str):
    """
    Отримати податкові налаштування користувача (група, ставки, ЗЕД).
    """
    try:
        response = supabase.table("fop_settings").select("*").eq("user_id", user_id).execute()
        
        # Якщо налаштувань ще немає, спробуємо створити дефолтні (або повернемо помилку)
        if not response.data:
            # Варіант: Створити дефолтні налаштування автоматично
            default_data = {
                "user_id": user_id,
                "fop_group": 3,
                "income_tax_percent": 5.0,
                "military_tax_percent": 1,
                "esv_value": 1760.0,
                "is_zed": False,
                "tax_system": "simplified",
                "activity_type": "services",
                "reporting_period": "quarter",
                "has_employees": False,
                "employees_count": 0,
                "is_vat_payer": False
            }
            new_settings = supabase.table("fop_settings").insert(default_data).execute()
            return new_settings.data[0]
            
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Error getting settings: {str(e)}")

@router.patch("/{user_id}")
def update_fop_settings(user_id: str, settings: FopSettingsUpdate):
    """
    Оновити налаштування (наприклад, змінити групу ФОП або ставку податку).
    """
    try:
        # exclude_unset=True гарантує, що ми оновлюємо тільки ті поля, які надіслав фронтенд
        update_data = settings.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="Немає даних для оновлення")

        # Спочатку перевіримо, чи існує запис
        check = supabase.table("fop_settings").select("setting_id").eq("user_id", user_id).execute()
        
        if not check.data:
            # Якщо запису немає - створюємо новий з переданими даними
            update_data["user_id"] = user_id
            response = supabase.table("fop_settings").insert(update_data).execute()
        else:
            # Якщо є - оновлюємо
            response = supabase.table("fop_settings")\
                .update(update_data)\
                .eq("user_id", user_id)\
                .execute()
            
        return response.data[0]
    except Exception as e:
        print(f"Settings Update Error: {e}")
        raise HTTPException(status_code=500, detail="Помилка оновлення налаштувань")