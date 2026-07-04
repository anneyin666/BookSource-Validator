# 校验服务
import httpx
import asyncio
import logging
from typing import List, Tuple, Optional, Callable
from datetime import datetime

from app.config import settings
from app.services.validation_strategy import get_retry_delay

logger = logging.getLogger(__name__)


class ValidatorService:
    """校验服务"""

    # 手机端请求头
    REQUEST_HEADERS = {
        "User-Agent": settings.MOBILE_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    MIN_CONCURRENCY = 1
    MAX_CONCURRENCY = 64
    MIN_TIMEOUT = 5
    MAX_TIMEOUT = 120

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
        timeout: int = None,
        client: Optional[httpx.AsyncClient] = None,
        max_retries: Optional[int] = None
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
        if max_retries is None:
            max_retries = settings.MAX_RETRIES

        async def do_request(client: httpx.AsyncClient) -> Tuple[bool, str]:
            """执行请求，返回 (是否有效, 原因)"""
            # 先尝试 HEAD 请求（更快）
            try:
                response = await client.head(
                    url,
                    headers=ValidatorService.REQUEST_HEADERS,
                    timeout=timeout,
                )
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
                async with client.stream(
                    "GET",
                    url,
                    headers=ValidatorService.REQUEST_HEADERS,
                    follow_redirects=True,
                    timeout=timeout,
                ) as response:
                    # 只需要状态码判断可访问性，不下载正文，避免小带宽服务器被页面内容拖慢。
                    if response.status_code == 403:
                        return True, "403-ignored"
                    if 200 <= response.status_code < 400:
                        return True, ""
                    return False, f"HTTP {response.status_code}"
                # 403 可能是 Cloudflare 防护，视为有效
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

        async def validate_with_client(request_client: httpx.AsyncClient) -> Tuple[bool, str]:
            # 重试机制
            for attempt in range(max_retries + 1):
                try:
                    is_valid, reason = await do_request(request_client)
                    if is_valid:
                        return True, ""

                    # 如果是最后一次尝试，直接返回失败
                    if attempt == max_retries:
                        logger.debug(f"校验失败 {url}: {reason}")
                        return False, reason

                    # 网络错误时重试
                    if reason in ["超时", "连接超时", "连接失败", "读取错误", "写入错误"]:
                        logger.debug(f"重试 {attempt + 1}/{max_retries} {url}: {reason}")
                        await asyncio.sleep(get_retry_delay(attempt, settings.RETRY_DELAY))
                        continue

                    return False, reason

                except httpx.TimeoutException:
                    if attempt == max_retries:
                        return False, "超时"
                    await asyncio.sleep(get_retry_delay(attempt, settings.RETRY_DELAY))
                except httpx.ConnectError:
                    if attempt == max_retries:
                        return False, "连接失败"
                    await asyncio.sleep(get_retry_delay(attempt, settings.RETRY_DELAY))
                except Exception as e:
                    logger.debug(f"校验异常 {url}: {type(e).__name__}: {str(e)}")
                    if attempt == max_retries:
                        return False, type(e).__name__
                    await asyncio.sleep(get_retry_delay(attempt, settings.RETRY_DELAY))

            return False, "重试耗尽"

        if client is not None:
            return await validate_with_client(client)

        # 兼容单次调用场景；批量校验应传入共享 client 以复用连接池。
        try:
            limits = httpx.Limits(max_connections=100, max_keepalive_connections=50)
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                max_redirects=settings.MAX_REDIRECTS,
                verify=False,
                limits=limits
            ) as request_client:
                return await validate_with_client(request_client)
        except httpx.TimeoutException:
            return False, "超时"
        except httpx.ConnectError:
            return False, "连接失败"
        except Exception as e:
            logger.debug(f"校验异常 {url}: {type(e).__name__}: {str(e)}")
            return False, type(e).__name__

    @staticmethod
    def create_validation_client(timeout: int) -> httpx.AsyncClient:
        """Create a shared HTTP client for a validation batch."""
        limits = httpx.Limits(max_connections=100, max_keepalive_connections=50)
        return httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            max_redirects=settings.MAX_REDIRECTS,
            verify=False,
            limits=limits
        )

    @staticmethod
    def clean_source_url(url: str) -> str:
        """Remove trailing Chinese notes that may be appended after a source URL."""
        import re
        chinese_match = re.search(r'[\u4e00-\u9fff]', url)
        if not chinese_match:
            return url

        chinese_index = chinese_match.start()
        slash_index = url.find('/', 8)
        if slash_index != -1 and chinese_index > slash_index:
            return url[:chinese_index]
        if chinese_index > 8:
            return url[:chinese_index]
        return url

    @staticmethod
    async def deep_validate(
        sources: List[dict],
        concurrency: int = 16,
        timeout: int = 30,
        max_retries: Optional[int] = None,
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
        concurrency = max(
            ValidatorService.MIN_CONCURRENCY,
            min(ValidatorService.MAX_CONCURRENCY, int(concurrency or 16)),
        )
        timeout = max(
            ValidatorService.MIN_TIMEOUT,
            min(ValidatorService.MAX_TIMEOUT, int(timeout or 30)),
        )

        valid = []
        failed_sources = {}  # {reason: [source_info]}
        total = len(sources)
        processed = 0
        lock = asyncio.Lock()

        semaphore = asyncio.Semaphore(concurrency)

        # 并发执行所有校验任务，并复用同一个 HTTP 客户端连接池。
        async with ValidatorService.create_validation_client(timeout) as client:
            async def validate_single_with_client(source: dict) -> Tuple[dict, bool, str]:
                nonlocal processed, valid, failed_sources

                url = ValidatorService.clean_source_url(source.get('bookSourceUrl', ''))
                name = source.get('bookSourceName', '')

                async with semaphore:
                    is_valid, reason = await ValidatorService.validate_source_access(
                        url,
                        timeout,
                        client=client,
                        max_retries=max_retries,
                    )

                    async with lock:
                        processed += 1
                        if is_valid:
                            valid.append(source)
                        else:
                            if reason not in failed_sources:
                                failed_sources[reason] = []
                            failed_source = source.copy()
                            failed_source.update({
                                'url': url,
                                'name': name,
                                'reason': reason,
                                '_failureReason': reason,
                            })
                            failed_sources[reason].append(failed_source)
                            logger.debug(f"无效书源 [{processed}/{total}]: {url} - {reason}")

                        if progress_callback:
                            progress_callback(processed, total, url, len(valid), len(failed_sources))

                    return source, is_valid, reason

            tasks = [validate_single_with_client(source) for source in sources]
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
