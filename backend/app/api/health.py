# 健康检查路由
from fastapi import APIRouter

from app.services.validation_strategy import PRESET_OPTIONS

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查（附带支持的模式，便于排查前后端版本不一致）"""
    return {"status": "ok", "presets": sorted(PRESET_OPTIONS.keys())}
