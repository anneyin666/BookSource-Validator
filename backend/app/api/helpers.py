# 路由层共享工具
"""路由层共享的结果组装与参数校验工具。

从 sources.py 抽离，避免单个路由文件继续膨胀，
同时供解析、校验、搜索等接口复用。
"""
from pathlib import Path
from typing import List

from app.models import SourceData
from app.services.search_validator import categorize_error, categorize_failed_sources
from app.services.validation_strategy import (
    ValidationOptions,
    normalize_validation_options,
)


def is_valid_source_file(filename: str) -> bool:
    """检查是否是有效的书源文件格式（.json 或 .txt）"""
    if not filename:
        return False
    lower_name = filename.lower()
    return lower_name.endswith('.json') or lower_name.endswith('.txt')


def validate_runtime_options(
    concurrency,
    timeout,
    validation_mode: str = "custom",
    smart_enabled=True,
) -> ValidationOptions:
    """校验并归一化运行时参数。"""
    return normalize_validation_options(
        concurrency=concurrency,
        timeout=timeout,
        mode=validation_mode,
        smart_enabled=smart_enabled,
    )


def calculate_rule_type_stats(valid_sources: List[dict], failed_sources: dict) -> dict:
    """
    计算规则类型统计

    Args:
        valid_sources: 有效书源列表
        failed_sources: 失败书源字典

    Returns:
        规则类型统计字典
    """
    stats = {
        'searchOnly': {'valid': 0, 'invalid': 0, 'total': 0},
        'exploreOnly': {'valid': 0, 'invalid': 0, 'total': 0},
        'both': {'valid': 0, 'invalid': 0, 'total': 0},
        'none': {'valid': 0, 'invalid': 0, 'total': 0}
    }

    # 统计有效书源
    for source in valid_sources:
        rule_type = source.get('_ruleType', '未知')
        if rule_type == '仅搜索':
            stats['searchOnly']['valid'] += 1
            stats['searchOnly']['total'] += 1
        elif rule_type == '仅发现':
            stats['exploreOnly']['valid'] += 1
            stats['exploreOnly']['total'] += 1
        elif rule_type == '搜索+发现':
            stats['both']['valid'] += 1
            stats['both']['total'] += 1

    # 统计失败书源
    for reason, sources_list in failed_sources.items():
        for source in sources_list:
            rule_type = source.get('_ruleType', '未知')
            if reason == '无规则':
                stats['none']['invalid'] += 1
                stats['none']['total'] += 1
            elif rule_type == '仅搜索':
                stats['searchOnly']['invalid'] += 1
                stats['searchOnly']['total'] += 1
            elif rule_type == '仅发现':
                stats['exploreOnly']['invalid'] += 1
                stats['exploreOnly']['total'] += 1
            elif rule_type == '搜索+发现':
                stats['both']['invalid'] += 1
                stats['both']['total'] += 1
            elif rule_type == '无规则':
                stats['none']['invalid'] += 1
                stats['none']['total'] += 1
            else:
                # 根据原因判断类型
                if '无搜索规则' in reason:
                    stats['exploreOnly']['invalid'] += 1
                    stats['exploreOnly']['total'] += 1
                elif '无发现规则' in reason:
                    stats['searchOnly']['invalid'] += 1
                    stats['searchOnly']['total'] += 1
                else:
                    # 默认归类
                    stats['both']['invalid'] += 1
                    stats['both']['total'] += 1

    return stats


def append_failed_source(
    failed_sources: dict,
    reason: str,
    source: dict,
    url: str,
    name: str,
) -> None:
    """Append a failed source while preserving original source fields for retry/export."""
    if reason not in failed_sources:
        failed_sources[reason] = []
    failed_source = source.copy()
    failed_source.update({
        "url": url,
        "name": name,
        "reason": reason,
        "_failureReason": reason,
    })
    failed_sources[reason].append(failed_source)


def build_failed_groups(failed_sources: dict) -> list:
    """Build sorted failed groups from reason-indexed failed sources.

    Each group carries a `category` (fixable/unfixable/checkable) so the
    frontend no longer needs to match Chinese reason keywords when deciding
    which failures are worth retrying.
    """
    failed_groups = []
    for reason, sources_list in failed_sources.items():
        failed_groups.append({
            "reason": reason,
            "category": categorize_error(reason),
            "count": len(sources_list),
            "sources": sources_list,
        })
    failed_groups.sort(key=lambda x: x["count"], reverse=True)
    return failed_groups


def build_strategy_payload(session) -> dict:
    """构造校验策略快照，供 SSE 进度与结果接口复用。"""
    return {
        "mode": session.validation_mode,
        "smartEnabled": session.smart_enabled,
        "phase": session.validation_phase,
        "currentConcurrency": session.current_concurrency,
        "currentTimeout": session.current_timeout,
    }


def build_session_result(session) -> dict:
    """构造完整校验结果（供结果接口使用，含书源明细）。"""
    raw_valid_sources = session.valid_sources
    failed_sources = session.failed_sources
    failed_groups = build_failed_groups(failed_sources)
    invalid_count = sum(len(items) for items in failed_sources.values())

    # 内部字段（_ruleType 等）只用于统计，不下发给前端/导出文件
    valid_sources = [
        {
            key: value
            for key, value in source.items()
            if not str(key).startswith('_')
        }
        for source in raw_valid_sources
    ]

    result = {
        "status": session.status,
        "total": session.total,
        "dedupCount": session.dedup_count if session.dedup_count else session.total,
        "duplicates": session.duplicates,
        "formatInvalid": session.format_invalid,
        "totalOriginal": session.total_original if session.total_original else session.total,
        "validCount": len(valid_sources),
        "invalidCount": invalid_count,
        "validSources": valid_sources,
        "failedGroups": failed_groups,
        "failedCategories": categorize_failed_sources(failed_groups),
        "fileStats": session.file_stats,
        "urlStats": session.url_stats,
        "strategy": build_strategy_payload(session),
    }
    if session.is_search:
        result["ruleTypeStats"] = calculate_rule_type_stats(
            raw_valid_sources, failed_sources
        )
    return result


def build_empty_source_data(*, file_stats=None, url_stats=None) -> SourceData:
    """构造空结果，避免错误分支触发响应模型校验失败。"""
    return SourceData(
        total=0,
        dedupCount=0,
        duplicates=0,
        duplicateUrls=[],
        formatInvalid=0,
        deepInvalid=None,
        validCount=0,
        dedupedSources=[],
        fileStats=file_stats,
        urlStats=url_stats
    )


def normalize_export_filename(filename: str) -> str:
    """标准化导出文件名。"""
    safe_name = Path(filename or "").name.strip()
    if not safe_name:
        safe_name = "阅读书源_去重有效.json"
    if not safe_name.lower().endswith(".json"):
        safe_name = f"{safe_name}.json"
    return safe_name
