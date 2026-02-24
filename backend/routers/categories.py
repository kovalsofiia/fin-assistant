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
        
        # 4. Фільтруємо дублікати (якщо користувач перекриває системну категорію своєю)
        # Групуємо по (name, type)
        merged_categories = {}
        for cat in response.data:
            key = (cat['name'], cat['type'])
            # Якщо вже є така категорія і вона належить користувачу - ігноруємо системну
            if key in merged_categories:
                if merged_categories[key]['user_id'] is None and cat['user_id'] is not None:
                    merged_categories[key] = cat
            else:
                merged_categories[key] = cat
        
        final_list = list(merged_categories.values())
        income_cats = [c for c in final_list if c['type'] == 'income']
        expense_cats = [c for c in final_list if c['type'] == 'expense']
        
        return {
            "income": income_cats,
            "expense": expense_cats,
            "all": final_list,
            "user_is_fop": user_is_fop
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
            "user_id": cat.user_id,
            "is_fop_only": cat.is_fop_only
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
    """Оновити власну категорію або створити копію системної"""
    try:
        data_to_update = {}
        if payload.get("name"):
            data_to_update["name"] = payload.get("name")
        if "is_fop_only" in payload:
            data_to_update["is_fop_only"] = payload.get("is_fop_only")

        if not data_to_update:
            raise HTTPException(status_code=400, detail="No fields to update")

        # 1. Перевіряємо категорію
        cat_res = supabase.table("categories").select("*").eq("id", category_id).execute()
        if not cat_res.data:
            raise HTTPException(status_code=404, detail="Категорію не знайдено")
        
        target_cat = cat_res.data[0]

        # 2. Якщо категорія системна (user_id is None), створюємо НОВУ для користувача
        if target_cat['user_id'] is None:
            new_cat_data = {
                "name": data_to_update.get("name", target_cat["name"]),
                "type": target_cat["type"],
                "user_id": user_id,
                "is_fop_only": data_to_update.get("is_fop_only", target_cat.get("is_fop_only", True))
            }
            response = supabase.table("categories").insert(new_cat_data).execute()
        else:
            # 3. Якщо категорія вже належить користувачу - просто оновлюємо
            if target_cat['user_id'] != user_id:
                raise HTTPException(status_code=403, detail="Ви не можете змінити категорію іншого користувача")
                
            response = supabase.table("categories").update(data_to_update)\
                .eq("id", category_id)\
                .eq("user_id", user_id)\
                .execute()
            
        if not response.data:
            raise HTTPException(status_code=500, detail="Не вдалося зберегти зміни")
            
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))