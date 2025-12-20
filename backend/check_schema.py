import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

try:
    # Try to fetch one row to see columns
    response = supabase.table("fop_settings").select("*").limit(1).execute()
    if response.data:
        print("Columns in fop_settings:", response.data[0].keys())
    else:
        print("Table fop_settings is empty, cannot determine columns this way.")
        # Alternatively, try to insert a dummy row or something? No, let's try another approach.
except Exception as e:
    print("Error fetching from fop_settings:", e)
