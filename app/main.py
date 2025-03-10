from fastapi import FastAPI

from api.routes import auth_router, telegram_router, scheduler_router

app = FastAPI(
    title="My Application API (Celery + SQLA Beat)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(auth_router, prefix="/auth")
app.include_router(telegram_router, prefix="/bot")
app.include_router(scheduler_router, prefix="/scheduler")

@app.get("/")
async def healthcheck():
    return {"status": "ok"}
