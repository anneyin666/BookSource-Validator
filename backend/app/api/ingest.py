# 书源读取工具
"""上传文件与在线链接的书源读取工具。

统一处理文件格式校验、大小限制、JSON 解析与 URL 安全校验，
供普通解析与 SSE 校验接口复用，避免同一套读取逻辑在多个端点重复。
"""
import json
import logging
from typing import List, Optional, Tuple

import httpx

from app.api.helpers import is_valid_source_file
from app.config import settings
from app.services.parser import ParserService
from app.services.url_security import UrlSecurityService

logger = logging.getLogger(__name__)


async def load_sources_from_upload(file) -> Tuple[Optional[List[dict]], Optional[str]]:
    """读取单个上传文件并提取书源。

    Returns:
        (书源列表, 错误信息)；成功时错误信息为 None。
    """
    if not is_valid_source_file(file.filename):
        return None, "仅支持 JSON 或 TXT 格式文件"

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        return (
            None,
            f"文件大小超过限制（最大{settings.MAX_FILE_SIZE // 1024 // 1024}MB）",
        )

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return None, f"JSON 解析失败：{str(e)}"

    if not ParserService.validate_json_structure(data):
        return None, "书源数据格式不正确"

    return ParserService.extract_sources(data), None


async def collect_sources_from_files(
    files: List,
) -> Tuple[List[dict], List[dict]]:
    """读取多个上传文件并合并书源。

    Returns:
        (合并后的书源列表, 文件统计列表)
    """
    all_sources: List[dict] = []
    file_stats: List[dict] = []

    for file in files:
        if not is_valid_source_file(file.filename):
            file_stats.append({
                "name": file.filename or "unknown",
                "valid": False,
                "error": "仅支持JSON/TXT格式",
            })
            continue

        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            file_stats.append({"name": file.filename, "valid": False, "error": "文件过大"})
            continue

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            file_stats.append({
                "name": file.filename,
                "valid": False,
                "error": f"JSON解析失败: {str(e)}",
            })
            continue
        except Exception as e:  # noqa: BLE001 - 读取异常需按文件隔离
            file_stats.append({"name": file.filename, "valid": False, "error": str(e)})
            continue

        if not ParserService.validate_json_structure(data):
            file_stats.append({"name": file.filename, "valid": False, "error": "格式不正确"})
            continue

        sources = ParserService.extract_sources(data)
        all_sources.extend(sources)
        file_stats.append({"name": file.filename, "valid": True, "count": len(sources)})
        logger.info("文件 %s: %s 条书源", file.filename, len(sources))

    return all_sources, file_stats


async def fetch_sources_from_url(
    url: str,
    client: httpx.AsyncClient,
) -> Tuple[Optional[List[dict]], Optional[str]]:
    """拉取单个在线书源链接。

    Returns:
        (书源列表, 错误信息)；成功时错误信息为 None。
    """
    if not url.startswith(('http://', 'https://')):
        return None, "无效URL"

    is_safe, error_message = await UrlSecurityService.is_safe_remote_url(url)
    if not is_safe:
        return None, error_message

    try:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        return None, "连接超时"
    except httpx.HTTPStatusError as e:
        return None, f"HTTP {e.response.status_code}"
    except json.JSONDecodeError:
        return None, "响应不是有效JSON"
    except Exception as e:  # noqa: BLE001 - 单个链接失败不影响其他链接
        return None, str(e)

    if not ParserService.validate_json_structure(data):
        return None, "格式不正确"

    return ParserService.extract_sources(data), None


async def collect_sources_from_urls(
    urls: List[str],
) -> Tuple[List[dict], List[dict]]:
    """拉取多个在线书源链接并合并。

    Returns:
        (合并后的书源列表, 链接统计列表)
    """
    all_sources: List[dict] = []
    url_stats: List[dict] = []

    async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
        for url in urls:
            sources, error_message = await fetch_sources_from_url(url, client)

            if error_message:
                url_stats.append({"url": url, "valid": False, "error": error_message})
                continue

            count = len(sources or [])
            all_sources.extend(sources or [])
            url_stats.append({"url": url, "valid": True, "count": count})
            logger.info("URL %s: %s 条书源", url, count)

    return all_sources, url_stats
