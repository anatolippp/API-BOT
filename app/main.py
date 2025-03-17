from fastapi import FastAPI

from api.routes import auth_router, telegram_router, scheduler_router
from api.user_routes import router as user_router
from api.project_routes import router as project_router

app = FastAPI(
    title="My Application API (Celery + SQLA Beat)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(auth_router, prefix="/auth")
app.include_router(telegram_router, prefix="/bot")
app.include_router(scheduler_router, prefix="/scheduler")

app.include_router(user_router, prefix="/api", tags=["Users"])

app.include_router(project_router, prefix="/api", tags=["Projects"])

@app.get("/")
async def healthcheck():
    return {"status": "ok"}
