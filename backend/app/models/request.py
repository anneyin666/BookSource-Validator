# 请求模型
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class UrlParseRequest(BaseModel):
    """URL解析请求"""
    url: str
    mode: Literal["dedup", "full"] = "dedup"
    concurrency: int = Field(default=16, ge=1, le=32, description="并发数")
    timeout: int = Field(default=30, description="超时时间（秒）")
    filter_types: str = Field(default="", description="过滤类型（逗号分隔）")


class ValidateStartRequest(BaseModel):
    """开始深度校验请求"""
    sources: List[dict]
    sessionId: Optional[str] = None
    concurrency: int = Field(default=16, ge=1, le=32, description="并发数")
    timeout: int = Field(default=30, description="超时时间（秒）")


class ValidateCancelRequest(BaseModel):
    """取消校验请求"""
    sessionId: str