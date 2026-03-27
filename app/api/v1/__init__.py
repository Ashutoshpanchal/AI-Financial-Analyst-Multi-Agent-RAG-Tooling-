from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.analyst import router as analyst_router
from app.api.v1.documents import router as documents_router
from app.api.v1.mcp_status import router as mcp_status_router
from app.api.v1.eval import router as eval_router
from app.api.v1.stock import router as stock_router

# Central v1 router — all v1 endpoints registered here
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router, tags=["Health"])
api_v1_router.include_router(analyst_router, tags=["Analyst"])
api_v1_router.include_router(documents_router, tags=["Documents"])
api_v1_router.include_router(mcp_status_router, tags=["MCP"])
api_v1_router.include_router(eval_router, tags=["Evaluation"])
api_v1_router.include_router(stock_router, tags=["Stock"])
