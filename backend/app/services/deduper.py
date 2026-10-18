# 去重服务
from typing import List, Tuple, Dict
import logging
from collections import Counter

from app.utils.url_utils import normalize_source_url

logger = logging.getLogger(__name__)


class DeduperService:
    """去重服务"""

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        URL标准化处理（委托给公共工具，保持兼容）

        - 转小写
        - 去除尾部斜杠
        - 去除空白字符
        - 去除 # 及后面的制作者信息（如 #@遇知、#🎃）
        - 去除URL后面直接跟着的中文作者信息（如 https://example.com细雨尘寰）
        """
        return normalize_source_url(url)

    @staticmethod
    def dedupe(sources: List[dict]) -> Tuple[List[dict], int, List[Dict]]:
        """
        去重处理

        Args:
            sources: 书源列表

        Returns:
            (去重后的列表, 重复数量, 重复URL统计列表)
        """
        seen = set()
        deduped = []
        duplicate_count = 0
        url_counter = Counter()  # 统计所有URL出现次数

        # 第一遍：统计所有URL出现次数
        for source in sources:
            url = source.get('bookSourceUrl', '')
            if isinstance(url, str):
                normalized_url = DeduperService.normalize_url(url)
            else:
                normalized_url = ''
            if normalized_url:
                url_counter[normalized_url] += 1

        # 第二遍：去重
        for source in sources:
            url = source.get('bookSourceUrl', '')
            if isinstance(url, str):
                original_url = url
                normalized_url = DeduperService.normalize_url(url)
            else:
                original_url = ''
                normalized_url = ''

            if not normalized_url:
                # 空URL的书源也保留
                deduped.append(source)
                continue

            if normalized_url not in seen:
                seen.add(normalized_url)
                deduped.append(source)
            else:
                duplicate_count += 1
                logger.debug(f"发现重复URL: {original_url}")

        # 提取重复URL统计（出现次数>1的）
        duplicate_urls = [
            {"url": url, "count": count}
            for url, count in url_counter.most_common(20)
            if count > 1
        ]

        logger.info(f"去重完成: 原始{len(sources)}条, 去重后{len(deduped)}条, 重复{duplicate_count}条")
        return deduped, duplicate_count, duplicate_urls