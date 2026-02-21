from typing import Optional
from fastapi import APIRouter, HTTPException
from core.database import supabase
from models.category import CategoryCreate

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("/")
def get_categories(user_id: Optional[str] = None):
    """
    Отримує список категорій.
    Адаптується під тип користувача (ФОП чи ні).
    """
    try:
        # 1. Визначаємо статус користувача (ФОП чи ні?)
        user_is_fop = True # За замовчуванням (якщо user_id не передали або сталася помилка)
        
        if user_id:
            profile_response = supabase.table("profiles").select("is_fop").eq("id", user_id).execute()
            if profile_response.data:
                user_is_fop = profile_response.data[0]['is_fop']

        # 2. Будуємо запит на категорії
        query = supabase.table("categories").select("*")
        
        # Фільтр по власнику (Системні + Свої)
        if user_id:
            query = query.or_(f"user_id.is.null,user_id.eq.{user_id}")
        else:
            query = query.is_("user_id", "null")
            
        # 3. Фільтр "ФОП / Не ФОП"
        # Якщо користувач НЕ ФОП -> показуємо тільки ті, де is_fop_only = FALSE
        # Якщо користувач ФОП -> показуємо ВСЕ (фільтр не потрібен)
        if not user_is_fop:
            query = query.eq("is_fop_only", False)

        response = query.execute()
        
        income_cats = [c for c in response.data if c['type'] == 'income']
        expense_cats = [c for c in response.data if c['type'] == 'expense']
        
        return {
            "income": income_cats,
            "expense": expense_cats,
            "all": response.data,
            "user_is_fop": user_is_fop # Повертаємо фронтенду інфо про статус
        }
    except Exception as e:
        print(f"Categories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
def create_category(cat: CategoryCreate):
    """Створити нову категорію користувача"""
    try:
        data = {
            "name": cat.name,
            "type": cat.type,
            "user_id": cat.user_id
        }
        response = supabase.table("categories").insert(data).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{category_id}")
def delete_category(category_id: str, user_id: str):
    """Видалити власну категорію та перенести транзакції в 'None'"""
    try:
        # 1. Отримуємо категорію, яку хочемо видалити
        cat_res = supabase.table("categories").select("*") \
            .eq("id", category_id) \
            .eq("user_id", user_id) \
            .execute()
        
        if not cat_res.data:
            raise HTTPException(status_code=403, detail="Не можна видалити цю категорію (можливо, вона системна або не знайдена)")
        
        cat_to_delete = cat_res.data[0]
        cat_type = cat_to_delete['type']
        
        # Забороняємо видаляти саму категорію 'None'
        if cat_to_delete['name'] == 'None':
            raise HTTPException(status_code=400, detail="Не можна видалити категорію 'None'")

        # 2. Шукаємо або створюємо категорію 'None' для цього користувача та типу
        none_res = supabase.table("categories").select("*") \
            .eq("user_id", user_id) \
            .eq("type", cat_type) \
            .eq("name", "None") \
            .execute()
        
        if none_res.data:
            none_id = none_res.data[0]['id']
        else:
            # Створюємо 'None'
            new_none = supabase.table("categories").insert({
                "name": "None",
                "type": cat_type,
                "user_id": user_id
            }).execute()
            if not new_none.data:
                raise HTTPException(status_code=500, detail="Не вдалося створити категорію 'None'")
            none_id = new_none.data[0]['id']

        # 3. Переприв'язуємо транзакції
        supabase.table("transactions").update({"category_id": none_id}) \
            .eq("category_id", category_id) \
            .eq("user_id", user_id) \
            .execute()

        # 4. Видаляємо стару категорію
        response = supabase.table("categories").delete() \
            .eq("id", category_id) \
            .eq("user_id", user_id) \
            .execute()
            
        return {"message": "Категорію видалено, транзакції перенесено до 'None'"}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        print(f"Delete category error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{category_id}")
def update_category(category_id: str, user_id: str, payload: dict):
    """Оновити назву власної категорії"""
    try:
        new_name = payload.get("name")
        if not new_name:
            raise HTTPException(status_code=400, detail="Назва не може бути порожньою")

        response = supabase.table("categories").update({"name": new_name})\
            .eq("id", category_id)\
            .eq("user_id", user_id)\
            .execute()
            
        if not response.data:
            raise HTTPException(status_code=403, detail="Не можна змінити цю категорію (вона системна або не знайдена)")
            
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))