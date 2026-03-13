# API路由导出
from fastapi import APIRouter
from .health import router as health_router
from .sources import router as sources_router

# 创建总路由
router = APIRouter()

# 注册子路由
router.include_router(health_router, tags=["health"])
router.include_router(sources_router, tags=["sources"])

__all__ = ["router"]