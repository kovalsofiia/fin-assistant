from fastapi import APIRouter, HTTPException
from core.database import supabase
from models.profile import ProfileCreate, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["Profiles"])

@router.post("/", status_code=201)
def create_profile(profile: ProfileCreate):
    """
    Явне створення профілю (якщо авто-тригер не спрацював).
    """
    try:
        # Перевірка, чи профіль вже існує
        existing = supabase.table("profiles").select("id").eq("id", profile.user_id).execute()
        if existing.data:
            raise HTTPException(status_code=409, detail="Профіль для цього користувача вже існує")

        data = {
            "id": profile.user_id,
            "is_fop": profile.is_fop,
            "full_name": profile.full_name
        }
        response = supabase.table("profiles").insert(data).execute()
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Помилка створення профілю: {str(e)}")

@router.get("/{user_id}")
def get_profile(user_id: str):
    """
    Отримати профіль. 
    Більше не створює 'фейковий' профіль, якщо його немає в БД, 
    а чесно каже 404 (або фронтенд має викликати POST).
    """
    try:
        response = supabase.table("profiles").select("*").eq("id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Профіль не знайдено")
            
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{user_id}")
def update_profile(user_id: str, profile: ProfileUpdate):
    """
    Оновлення даних. Валідація через Pydantic не пропустить довгі імена.
    """
    try:
        # exclude_unset=True: беремо тільки ті поля, які реально передали в JSON
        update_data = profile.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="Не передано даних для оновлення")

        response = supabase.table("profiles").update(update_data).eq("id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Профіль не знайдено для оновлення")
            
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}")
def delete_profile(user_id: str):
    """
    Повне видалення профілю (GDPR).
    Увага: це видалить запис з profiles, але user в auth.users залишиться.
    """
    try:
        response = supabase.table("profiles").delete().eq("id", user_id).execute()
        
        if not response.data:
             raise HTTPException(status_code=404, detail="Профіль не знайдено")
             
        return {"message": "✅ Профіль успішно видалено"}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))
    
