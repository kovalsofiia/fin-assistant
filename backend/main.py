from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import transactions, categories, profiles, settings

app = FastAPI(title="FOP Assistant API 🇺🇦")

# 2. CORS (Дозволяємо фронтенду доступ)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "active", "service": "FOP Assistant Modular Backend"}

# Підключаємо модулі
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(profiles.router)
app.include_router(settings.router)