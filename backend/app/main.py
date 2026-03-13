# FastAPI应用入口
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import router

# 创建应用
app = FastAPI(
    title="阅读书源去重校验工具 API",
    description="开源阅读 App 书源文件处理工具 - 支持去重、格式校验、深度校验",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api")


# 根路径
@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }