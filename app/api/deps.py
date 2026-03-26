from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.config.settings import Settings, get_settings

# Reusable type aliases for dependency injection
# Usage in routes:  async def my_route(db: DBSession, settings: AppSettings)

DBSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
