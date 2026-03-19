# FastAPI应用入口
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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

# 生产环境：静态文件服务
# 前端构建后的 dist 目录路径
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

# 检查是否为生产环境（dist 目录存在）
if FRONTEND_DIST.exists() and FRONTEND_DIST.is_dir():
    # 挂载静态资源目录（JS、CSS、图片等）
    assets_path = FRONTEND_DIST / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

    # SPA 路由处理：所有非 API 路由返回 index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """
        处理 SPA 路由
        所有非 API、非静态文件的请求都返回 index.html
        """
        # API 路由由 router 处理
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not Found")
        # 静态文件（带扩展名）尝试直接返回
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # 其他路由返回 index.html（SPA 路由）
        index_path = FRONTEND_DIST / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"error": "File not found"}


# 根路径（开发环境使用）
@app.get("/")
async def root():
    # 生产环境下由 SPA 处理
    if FRONTEND_DIST.exists():
        return FileResponse(str(FRONTEND_DIST / "index.html"))
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }
