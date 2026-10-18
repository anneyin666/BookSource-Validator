# URL 清洗与标准化工具
"""书源 URL 清洗与标准化工具。

统一维护去重、深度校验、搜索校验共用的 URL 处理逻辑，
避免多处复制实现导致规则漂移。
"""
import re

# 中文字符（CJK 统一表意文字）
CHINESE_CHAR_RE = re.compile(r'[\u4e00-\u9fff]')

# scheme:// 前缀（http://、https:// 等）
SCHEME_PREFIX_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.\-]*://')


def strip_chinese_suffix(url: str) -> str:
    """去除拼接在 URL 域名/路径之后的中文作者信息。

    示例:
        https://example.com细雨尘寰 -> https://example.com
        https://example.com/path作者 -> https://example.com/path

    规则:
    - 中文出现在路径分隔符之后 -> 截断
    - 无路径分隔符且中文位于域名之后 -> 截断
    - 中文出现在域名内部（如中文域名）-> 保留

    兼容任意长度的 scheme（不再假设前缀固定为 8 个字符），
    无 scheme 的裸域名同样适用。
    """
    if not url:
        return url

    match = CHINESE_CHAR_RE.search(url)
    if not match:
        return url

    chinese_index = match.start()
    scheme_match = SCHEME_PREFIX_RE.match(url)
    scheme_len = scheme_match.end() if scheme_match else 0

    # 域名后的第一个路径斜杠（域名至少应有 1 个字符）
    path_slash_index = url.find('/', scheme_len + 1)
    if path_slash_index != -1 and chinese_index > path_slash_index:
        return url[:chinese_index]
    if chinese_index > scheme_len:
        return url[:chinese_index]
    return url


def normalize_source_url(url: str) -> str:
    """去重比较用的 URL 标准化。

    - 去除首尾空白并转小写
    - 去除 # 及其后的制作者信息（如 #@遇知）
    - 去除拼接在 URL 后的中文作者信息
    - 去除尾部斜杠
    """
    if not url:
        return ''
    url = url.strip().lower()

    hash_index = url.find('#')
    if hash_index != -1:
        url = url[:hash_index]

    url = strip_chinese_suffix(url)

    while url.endswith('/'):
        url = url[:-1]
    return url
