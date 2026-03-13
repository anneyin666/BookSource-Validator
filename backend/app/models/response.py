# 响应模型
from typing import List, Optional, Any, Dict
from pydantic import BaseModel


class DuplicateUrl(BaseModel):
    """重复URL信息"""
    url: str
    count: int  # 出现次数


class FailedSource(BaseModel):
    """失败书源信息"""
    url: str
    name: str = ""
    reason: str  # 失败原因


class FailedSourceGroup(BaseModel):
    """失败书源分组"""
    reason: str  # 失败原因
    count: int  # 数量
    sources: List[FailedSource]  # 书源列表


class SourceData(BaseModel):
    """书源数据响应"""
    total: int
    dedupCount: int
    duplicates: int = 0  # 重复数量
    duplicateUrls: List[DuplicateUrl] = []  # 重复URL列表（前10个）
    formatInvalid: int
    deepInvalid: Optional[int] = None
    validCount: int
    dedupedSources: List[dict]
    failedGroups: Optional[List[FailedSourceGroup]] = None  # 失败书源分组
    # 批量处理统计
    fileStats: Optional[List[dict]] = None  # 文件统计
    urlStats: Optional[List[dict]] = None  # URL统计


class ParseResponse(BaseModel):
    """解析响应"""
    code: int = 200
    message: str = "success"
    data: Optional[SourceData] = None


class ValidateProgressData(BaseModel):
    """校验进度数据"""
    processed: int
    total: int
    current: str
    valid: int
    invalid: int


class ValidateCompleteData(BaseModel):
    """校验完成数据"""
    total: int
    valid: int
    invalid: int
    dedupedSources: List[dict]