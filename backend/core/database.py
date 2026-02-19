from supabase import create_client, Client
from core.config import settings

if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
    raise ValueError("Помилка: Немає ключів Supabase у .env. Перевір файл!")

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)