# 校验服务
import httpx
import asyncio
import logging
from typing import List, Tuple, Optional, Callable
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


class ValidatorService:
    """校验服务"""

    # 手机端请求头
    REQUEST_HEADERS = {
        "User-Agent": settings.MOBILE_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    # 支持的并发数选项
    CONCURRENCY_OPTIONS = [1, 4, 8, 16, 32]

    # 支持的超时选项
    TIMEOUT_OPTIONS = settings.TIMEOUT_OPTIONS

    @staticmethod
    def is_format_valid(source: dict) -> bool:
        """
        判断书源格式是否有效

        条件：
        - bookSourceUrl 字段存在
        - 不为空字符串
        - 以 http:// 或 https:// 开头
        """
        url = source.get('bookSourceUrl', '')
        if not url or not isinstance(url, str):
            return False
        url = url.strip()
        return url.startswith(('http://', 'https://'))

    @staticmethod
    def format_validate(sources: List[dict]) -> Tuple[List[dict], int]:
        """
        格式校验

        Returns:
            (有效的书源列表, 失效数量)
        """
        valid = []
        invalid = 0

        for source in sources:
            if ValidatorService.is_format_valid(source):
                valid.append(source)
            else:
                invalid += 1

        return valid, invalid

    @staticmethod
    async def validate_source_access(
        url: str,
        timeout: int = None
    ) -> Tuple[bool, str]:
        """
        深度校验单个书源

        Args:
            url: 书源URL
            timeout: 超时时间（秒）

        Returns:
            (是否有效, 失败原因) - 有效时原因为空或"403-ignored"
        """
        if timeout is None:
            timeout = settings.VALIDATE_TIMEOUT

        async def do_request(client: httpx.AsyncClient) -> Tuple[bool, str]:
            """执行请求，返回 (是否有效, 原因)"""
            # 先尝试 HEAD 请求（更快）
            try:
                response = await client.head(url, headers=ValidatorService.REQUEST_HEADERS)
                # 403 可能是 Cloudflare 防护，视为有效
                if response.status_code == 403:
                    return True, "403-ignored"
                if 200 <= response.status_code < 400:
                    return True, ""
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    return True, "403-ignored"
            except Exception as e:
                logger.debug(f"HEAD请求失败 {url}: {type(e).__name__}")

            # HEAD 失败后尝试 GET 请求（部分网站不支持HEAD）
            try:
                response = await client.get(
                    url,
                    headers=ValidatorService.REQUEST_HEADERS,
                    follow_redirects=True
                )
                # 403 可能是 Cloudflare 防护，视为有效
                if response.status_code == 403:
                    return True, "403-ignored"
                if 200 <= response.status_code < 400:
                    return True, ""
                return False, f"HTTP {response.status_code}"
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    return True, "403-ignored"
                return False, f"HTTP {e.response.status_code}"
            except httpx.TimeoutException:
                return False, "超时"
            except httpx.ConnectError:
                return False, "连接失败"
            except httpx.ConnectTimeout:
                return False, "连接超时"
            except httpx.ReadError:
                return False, "读取错误"
            except httpx.WriteError:
                return False, "写入错误"
            except Exception as e:
                return False, type(e).__name__

            return False, "未知错误"

        # 重试机制
        for attempt in range(settings.MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=True,
                    max_redirects=settings.MAX_REDIRECTS,
                    verify=False  # 忽略SSL证书验证
                ) as client:
                    is_valid, reason = await do_request(client)
                    if is_valid:
                        return True, ""

                    # 如果是最后一次尝试，直接返回失败
                    if attempt == settings.MAX_RETRIES:
                        logger.debug(f"校验失败 {url}: {reason}")
                        return False, reason

                    # 网络错误时重试
                    if reason in ["超时", "连接超时", "连接失败", "读取错误", "写入错误"]:
                        logger.debug(f"重试 {attempt + 1}/{settings.MAX_RETRIES} {url}: {reason}")
                        await asyncio.sleep(settings.RETRY_DELAY)
                        continue

                    return False, reason

            except httpx.TimeoutException:
                if attempt == settings.MAX_RETRIES:
                    return False, "超时"
                await asyncio.sleep(settings.RETRY_DELAY)
            except httpx.ConnectError:
                if attempt == settings.MAX_RETRIES:
                    return False, "连接失败"
                await asyncio.sleep(settings.RETRY_DELAY)
            except Exception as e:
                logger.debug(f"校验异常 {url}: {type(e).__name__}: {str(e)}")
                if attempt == settings.MAX_RETRIES:
                    return False, type(e).__name__
                await asyncio.sleep(settings.RETRY_DELAY)

        return False, "重试耗尽"

    @staticmethod
    async def deep_validate(
        sources: List[dict],
        concurrency: int = 16,
        timeout: int = 30,
        progress_callback: Optional[Callable[[int, int, str, int, int], None]] = None
    ) -> Tuple[List[dict], int, List[dict]]:
        """
        批量深度校验（并发）

        Args:
            sources: 书源列表
            concurrency: 并发数（默认16）
            timeout: 超时时间（默认30秒）
            progress_callback: 进度回调函数 (processed, total, current_url, valid_count, invalid_count)

        Returns:
            (有效的书源列表, 失效数量, 失败书源分组列表)
        """
        # 限制并发数在有效范围内
        if concurrency not in ValidatorService.CONCURRENCY_OPTIONS:
            concurrency = 16

        # 限制超时时间在有效范围内
        if timeout not in ValidatorService.TIMEOUT_OPTIONS:
            timeout = 30

        valid = []
        failed_sources = {}  # {reason: [source_info]}
        total = len(sources)
        processed = 0
        lock = asyncio.Lock()

        semaphore = asyncio.Semaphore(concurrency)

        async def validate_single(source: dict) -> Tuple[dict, bool, str]:
            """校验单个书源"""
            nonlocal processed, valid, failed_sources

            url = source.get('bookSourceUrl', '')
            name = source.get('bookSourceName', '')

            # 清理 URL 中的中文字符（如作者信息）
            import re
            chinese_match = re.search(r'[\u4e00-\u9fff]', url)
            if chinese_match:
                chinese_index = chinese_match.start()
                slash_index = url.find('/', 8)  # 跳过 http:// 或 https://
                if slash_index != -1 and chinese_index > slash_index:
                    url = url[:chinese_index]
                elif chinese_index > 8:
                    url = url[:chinese_index]

            async with semaphore:
                is_valid, reason = await ValidatorService.validate_source_access(url, timeout)

                async with lock:
                    processed += 1
                    if is_valid:
                        valid.append(source)
                    else:
                        # 记录失败书源
                        if reason not in failed_sources:
                            failed_sources[reason] = []
                        failed_sources[reason].append({
                            'url': url,
                            'name': name,
                            'reason': reason
                        })
                        logger.debug(f"无效书源 [{processed}/{total}]: {url} - {reason}")

                    # 进度回调
                    if progress_callback:
                        progress_callback(processed, total, url, len(valid), len(failed_sources))

                return source, is_valid, reason

        # 并发执行所有校验任务
        tasks = [validate_single(source) for source in sources]
        await asyncio.gather(*tasks)

        # 构建失败分组列表
        failed_groups = []
        for reason, sources_list in failed_sources.items():
            failed_groups.append({
                'reason': reason,
                'count': len(sources_list),
                'sources': sources_list
            })
        # 按数量降序排序
        failed_groups.sort(key=lambda x: x['count'], reverse=True)

        invalid = sum(g['count'] for g in failed_groups)
        logger.info(f"深度校验完成: 总数{total}, 有效{len(valid)}, 无效{invalid}")
        return valid, invalid, failed_groups

    @staticmethod
    def set_source_group(sources: List[dict], valid_count: int) -> None:
        """
        设置书源分组

        保留原有非校验分组，替换旧的校验分组
        格式：原分组,YYYY-MM-DD去重有效XXX条
        """
        import re
        date_str = datetime.now().strftime("%Y-%m-%d")
        new_group = f"{date_str}去重有效{valid_count}条"

        # 匹配旧的校验分组格式：YYYY-MM-DD去重有效XXX条
        validation_pattern = re.compile(r'\d{4}-\d{2}-\d{2}去重有效\d+条')

        for source in sources:
            original_group = source.get("bookSourceGroup", "")
            if original_group:
                # 移除旧的校验分组
                groups = [g.strip() for g in original_group.split(',')]
                filtered_groups = [g for g in groups if not validation_pattern.match(g)]
                # 添加新分组
                filtered_groups.append(new_group)
                source["bookSourceGroup"] = ','.join(filtered_groups)
            else:
                # 无原分组，直接设置
                source["bookSourceGroup"] = new_group