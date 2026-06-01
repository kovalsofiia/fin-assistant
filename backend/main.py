from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routers import transactions, categories, profiles, settings as app_settings, tax_rules, budgets, analytics, accounts, kveds

app = FastAPI(title=settings.PROJECT_NAME)

# 2. CORS (Дозволяємо фронтенду доступ)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
app.include_router(app_settings.router)
app.include_router(tax_rules.router)
app.include_router(budgets.router)
app.include_router(analytics.router)
app.include_router(accounts.router)
app.include_router(kveds.router)