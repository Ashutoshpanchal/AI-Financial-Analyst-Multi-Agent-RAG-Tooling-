from fastapi import APIRouter
from sqlalchemy import text
from app.api.deps import DBSession, AppSettings

router = APIRouter()


@router.get("/health")
async def health_check(db: DBSession, settings: AppSettings) -> dict:
    """
    Health check endpoint.
    Verifies the app is running and DB is reachable.
    """
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "environment": settings.app_env,
        "database": db_status,
    }
