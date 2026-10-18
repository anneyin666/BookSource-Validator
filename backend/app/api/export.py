# 书源导出路由
"""移动端临时导出链接路由。"""
import json
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.api.helpers import normalize_export_filename
from app.config import settings
from app.models import (
    BookSourceExportData,
    BookSourceExportRequest,
    BookSourceExportResponse,
)
from app.services.export_store import export_store

router = APIRouter()


@router.post("/export/book-source", response_model=BookSourceExportResponse)
async def create_book_source_export(payload: BookSourceExportRequest):
    """为移动端导出生成一个临时可访问的 JSON 链接。"""
    if not payload.sources:
        return BookSourceExportResponse(code=400, message="没有可导出的书源数据")

    filename = normalize_export_filename(payload.filename)
    content = json.dumps(payload.sources, ensure_ascii=False, indent=2)
    export_payload = await export_store.create_export(
        content=content,
        filename=filename,
        ttl_seconds=settings.EXPORT_TTL_SECONDS,
    )

    return BookSourceExportResponse(
        data=BookSourceExportData(
            exportId=export_payload.export_id,
            path=f"/api/export/book-source/{export_payload.export_id}",
            filename=export_payload.filename,
            expiresAt=export_payload.expires_at,
            ttlSeconds=settings.EXPORT_TTL_SECONDS,
        )
    )


@router.get("/export/book-source/{export_id}", name="download_exported_book_source")
async def download_exported_book_source(export_id: str):
    """下载临时导出的书源 JSON。"""
    export_payload = await export_store.get_export(export_id)
    if not export_payload:
        raise HTTPException(status_code=404, detail="导出链接不存在或已过期")

    quoted_filename = quote(export_payload.filename)
    headers = {
        "Cache-Control": "no-store, max-age=0",
        "Content-Disposition": (
            f"attachment; filename=book-sources.json; "
            f"filename*=UTF-8''{quoted_filename}"
        ),
    }
    return Response(
        content=export_payload.content,
        media_type="application/json",
        headers=headers,
    )


