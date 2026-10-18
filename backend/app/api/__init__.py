# API路由导出
"""API 路由聚合。"""
from fastapi import APIRouter

from .export import router as export_router
from .feedback import router as feedback_router
from .health import router as health_router
from .parse import router as parse_router
from .search import router as search_router
from .validate import router as validate_router

# 创建总路由
router = APIRouter()

# 注册子路由
router.include_router(health_router, tags=["health"])
router.include_router(feedback_router, tags=["feedback"])
router.include_router(parse_router, tags=["parse"])
router.include_router(validate_router, tags=["validate"])
router.include_router(search_router, tags=["search"])
router.include_router(export_router, tags=["export"])

__all__ = ["router"]
