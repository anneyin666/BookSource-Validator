# 健康检查路由
from fastapi import APIRouter

from app.services.validation_strategy import PRESET_OPTIONS

router = APIRouter()


@router.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    """健康检查（支持 GET/HEAD 探活，附带支持的模式）"""
    return {"status": "ok", "presets": sorted(PRESET_OPTIONS.keys())}
