# 应用配置
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    # 服务配置
    APP_NAME: str = "阅读书源去重校验工具"
    DEBUG: bool = True  # 开启调试模式

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # 文件限制
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # 请求超时
    REQUEST_TIMEOUT: int = 30
    EXPORT_TTL_SECONDS: int = 15 * 60  # 导出临时链接有效期（秒）

    # 深度校验超时选项（秒）
    TIMEOUT_OPTIONS: List[int] = [15, 30, 45, 60]
    VALIDATE_TIMEOUT: int = 30  # 默认超时

    # 重试配置
    MAX_RETRIES: int = 2  # 最大重试次数
    RETRY_DELAY: float = 1.0  # 重试间隔（秒）

    # 忽略的错误状态码（视为有效）
    IGNORE_STATUS_CODES: List[int] = [403]  # 403通常是Cloudflare防护

    # 手机端请求头
    MOBILE_USER_AGENT: str = (
        "Mozilla/5.0 (Linux; Android 12; SM-G991B) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    )

    # 最大重定向次数
    MAX_REDIRECTS: int = 5

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
