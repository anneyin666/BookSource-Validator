# JavaScript 规则处理器
import re
import hashlib
import base64
import time
import json
import logging
from typing import Optional, Tuple, Dict, Any
from urllib.parse import quote, urlparse

logger = logging.getLogger(__name__)


class JSRuleProcessor:
    """
    处理书源中的 JavaScript 规则

    阅读书源的 JS 代码通常运行在阅读 App 的 Java 环境中，
    这里提供基本的 JS 执行和 Java 方法模拟
    """

    @staticmethod
    def md5_encode(text: str) -> str:
        """MD5 加密"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    @staticmethod
    def base64_encode(text: str) -> str:
        """Base64 编码"""
        return base64.b64encode(text.encode('utf-8')).decode('utf-8')

    @staticmethod
    def base64_decode(text: str) -> str:
        """Base64 解码"""
        try:
            return base64.b64decode(text.encode('utf-8')).decode('utf-8')
        except:
            return text

    @staticmethod
    def get_timestamp() -> int:
        """获取当前时间戳（毫秒）"""
        return int(time.time() * 1000)

    @staticmethod
    def extract_url_from_js(js_code: str, keyword: str, source_url: str = "") -> Optional[str]:
        """
        从 JS 代码中提取 URL

        尝试解析简单的 JS 模板，提取最终 URL

        Args:
            js_code: JavaScript 代码
            keyword: 搜索关键词
            source_url: 书源基础URL

        Returns:
            提取的 URL 或 None
        """
        code = js_code

        # 1. 替换常见变量
        code = code.replace('{{key}}', keyword)
        code = code.replace('{key}', keyword)
        code = code.replace('{{page}}', '1')
        code = code.replace('{page}', '1')

        # 2. 提取 URL 模式
        # 模式1: 直接包含 http URL
        url_pattern = r'https?://[^\s\'"<>]+'
        urls = re.findall(url_pattern, code)
        if urls:
            # 返回最长的URL（通常是完整的API URL）
            # 但要排除包含变量占位符的URL
            valid_urls = [u for u in urls if '{{' not in u and '{' not in u]
            if valid_urls:
                return max(valid_urls, key=len)
            # 如果都有占位符，替换后返回
            if urls:
                url = max(urls, key=len)
                url = url.replace('{{key}}', quote(keyword))
                url = url.replace('{key}', quote(keyword))
                return url

        # 3. 检查是否是构建URL的模式
        # 例如: source.key + "/search?keyword=" + key
        if 'source.key' in code or 'source.getKey()' in code:
            # 尝试提取路径部分
            path_match = re.search(r'["\']([^"\']*search[^"\']*)["\']', code)
            if path_match:
                path = path_match.group(1)
                path = path.replace('{{key}}', quote(keyword))
                path = path.replace('{key}', quote(keyword))
                if source_url:
                    return source_url.rstrip('/') + '/' + path.lstrip('/')

        return None

    @staticmethod
    def parse_simple_js_url(js_code: str, keyword: str, source_url: str = "") -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        解析简单的 JS URL 构建代码

        Args:
            js_code: JavaScript 代码
            keyword: 搜索关键词
            source_url: 书源基础URL

        Returns:
            (是否成功, URL, 方法, POST数据)
        """
        code = js_code.strip()

        # 处理以 {{cookie.removeCookie 开头的代码
        if code.startswith('{{cookie.removeCookie') or '{{cookie' in code:
            # 提取 @js: 后面的代码
            if '@js:' in code:
                code = code.split('@js:')[-1].strip()

        # 模式0: 多行格式 - URL配置在前，@js: 在后
        # 格式: https://xxx.com/search,{"method":"POST","body":"..."}
        #       @js: ...JS代码...
        if '@js:' in code:
            # 分割 @js: 之前的部分
            parts = code.split('@js:')
            config_part = parts[0].strip()

            # 检查是否有JSON配置
            if config_part.startswith('http'):
                # 查找JSON部分
                if ',{' in config_part:
                    json_start = config_part.find('{')
                    if json_start > 0:
                        url_part = config_part[:json_start].rstrip(',').rstrip()
                        json_part = config_part[json_start:]
                        try:
                            config = json.loads(json_part)
                            method = config.get('method', 'GET').upper()
                            post_body = config.get('body', '')
                            post_body = post_body.replace('{{key}}', keyword)
                            post_body = post_body.replace('{key}', keyword)
                            return True, url_part, method, post_body
                        except:
                            pass
                else:
                    # 没有JSON配置，纯URL
                    return True, config_part, "GET", None

        # 模式A: java.ajax + Jsoup 解析模式（优先处理）
        # 这类代码需要动态获取数据，我们尝试构建合理的搜索URL
        if 'java.ajax' in code or 'org.jsoup' in code:
            lines = code.split('\n') if '\n' in code else [code]

            base_url = source_url
            search_path = "/search"
            method = "POST"
            post_body = ""
            has_dynamic_data = False

            for line in lines:
                line = line.strip()

                # 检查是否需要动态数据
                if 'token' in line.lower() or '.attr(' in line or '.select(' in line:
                    has_dynamic_data = True

                # 提取搜索路径 - 只匹配以 / 开头的路径
                path_match = re.search(r'["\'](/[a-zA-Z0-9_/-]*)["\']', line)
                if path_match and 'search' in path_match.group(1):
                    search_path = path_match.group(1)

                # 提取 POST body - 从 JSON.stringify 或 body= 中提取
                if 'JSON.stringify' in line:
                    json_match = re.search(r'JSON\.stringify\s*\(\s*\{([^}]+)\}\s*\)', line)
                    if json_match:
                        json_content = json_match.group(1)
                        # 提取 body
                        body_match = re.search(r'body["\']?\s*:\s*["\']([^"\']+)["\']', json_content)
                        if body_match:
                            post_body = body_match.group(1)
                        # 提取 method
                        method_match = re.search(r'method["\']?\s*:\s*["\']([^"\']+)["\']', json_content)
                        if method_match:
                            method = method_match.group(1).upper()

                # 直接的 body 赋值
                if 'body=' in line or 'body =' in line:
                    body_match = re.search(r'body\s*=\s*["\']([^"\']+)["\']', line)
                    if body_match:
                        post_body = body_match.group(1)

            # 替换关键词变量
            if post_body:
                post_body = post_body.replace('{{key}}', keyword)
                post_body = post_body.replace('{key}', keyword)
                post_body = post_body.replace('${key}', keyword)
                post_body = post_body.replace('key=', f'key={keyword}')
            else:
                post_body = f"searchkey={keyword}"

            # 构建URL
            if base_url:
                url = base_url.rstrip('/') + search_path

                if not post_body:
                    post_body = f"searchkey={keyword}"

                return True, url, method, post_body

        # 模式B: 简单的URL拼接
        # source.key + "/search" + ",{\"method\":\"POST\",\"body\":\"...\"}"
        if 'source.key' in code or 'source.getKey()' in code:
            base = source_url.rstrip('/') if source_url else ""

            # 提取路径和配置
            parts = re.findall(r'["\']([^"\']*)["\']', code)

            path = ""
            method = "GET"
            post_data = None

            for part in parts:
                if part.startswith('/') and not part.startswith('//'):
                    path = part
                elif part.startswith('{') or 'method' in part.lower() or 'body' in part.lower():
                    try:
                        config_str = part if part.startswith('{') else '{' + part + '}'
                        config = json.loads(config_str)
                        method = config.get('method', 'GET').upper()
                        post_data = config.get('body', '')
                        if post_data:
                            post_data = post_data.replace('{{key}}', keyword)
                            post_data = post_data.replace('{key}', keyword)
                    except:
                        pass

            if path or base:
                url = base + path if path.startswith('/') else base + '/' + path if path else base
                url = url.replace('{{key}}', quote(keyword))
                url = url.replace('{key}', quote(keyword))
                return True, url, method, post_data

        # 模式C: JSON.stringify 配置模式
        json_match = re.search(r'JSON\.stringify\s*\(\s*(\{[^}]+\})\s*\)', code)
        if json_match:
            try:
                config_str = json_match.group(1)
                config = json.loads(config_str)
                method = config.get('method', 'GET').upper()
                post_data = config.get('body', '')
                post_data = post_data.replace('{{key}}', keyword)
                post_data = post_data.replace('{key}', keyword)

                if source_url:
                    return True, source_url.rstrip('/') + '/search', method, post_data
            except:
                pass

        # 模式D: 直接提取URL
        url = JSRuleProcessor.extract_url_from_js(code, keyword, source_url)
        if url:
            return True, url, "GET", None

        return False, None, None, None

    @staticmethod
    def preprocess_js_code(js_code: str, keyword: str, source_url: str = "") -> str:
        """
        预处理 JS 代码，替换常见变量和函数

        Args:
            js_code: JavaScript 代码
            keyword: 搜索关键词
            source_url: 书源基础URL

        Returns:
            处理后的代码
        """
        code = js_code

        # 替换关键词变量
        code = code.replace('{{key}}', f'"{keyword}"')
        code = code.replace('{{key|encode}}', f'"{quote(keyword)}"')
        code = code.replace('{key}', f'"{keyword}"')

        # 替换时间戳
        code = re.sub(r'Date\.now\(\)', str(int(time.time() * 1000)), code)
        code = re.sub(r'new Date\(\)\.getTime\(\)', str(int(time.time() * 1000)), code)

        # 替换 source.key
        if source_url:
            code = code.replace('source.key', f'"{source_url}"')
            code = code.replace('source.getKey()', f'"{source_url}"')

        return code

    @staticmethod
    def try_execute_js(js_code: str, keyword: str, source_url: str = "") -> Tuple[bool, Optional[str], str]:
        """
        尝试执行 JavaScript 代码

        Args:
            js_code: JavaScript 代码
            keyword: 搜索关键词
            source_url: 书源基础URL

        Returns:
            (是否成功, 结果URL, 错误信息)
        """
        # 首先检测不支持的功能
        unsupported = JSRuleProcessor.detect_unsupported_features(js_code)
        if unsupported:
            return False, None, unsupported

        # 首先尝试简单解析
        success, url, method, post_data = JSRuleProcessor.parse_simple_js_url(js_code, keyword, source_url)
        if success and url:
            # 返回格式: URL 或 URL|METHOD|POST_DATA
            result = url
            if method and method != "GET":
                result = f"{url}|{method}"
                if post_data:
                    result = f"{result}|{post_data}"
            return True, result, ""

        # 尝试使用 js2py 执行
        try:
            import js2py

            # 预处理代码
            code = JSRuleProcessor.preprocess_js_code(js_code, keyword, source_url)

            # 创建模拟的 Java 对象
            java_object = f"""
            var source = {{
                key: "{source_url}",
                getKey: function() {{ return "{source_url}"; }}
            }};
            var java = {{
                md5Encode: function(text) {{ return md5(text); }},
                base64Encode: function(text) {{ return btoa(text); }},
                base64Decode: function(text) {{ return atob(text); }},
                ajax: function(url) {{ return url; }},
                connect: function(url) {{ return url; }},
                webView: function() {{ return ""; }},
                getString: function() {{ return ""; }}
            }};
            var Packages = {{
                java: {{
                    lang: {{
                        Thread: {{
                            sleep: function() {{}}
                        }}
                    }}
                }}
            }};
            """

            # 简化 org.jsoup 调用
            code = re.sub(r'org\.jsoup\.Jsoup\.parse\s*\([^)]+\)', '""', code)
            code = re.sub(r'\.select\s*\([^)]+\)', '""', code)
            code = re.sub(r'\.attr\s*\([^)]+\)', '""', code)

            # 构建完整的 JS 代码
            full_code = java_object + "\n" + code

            # 尝试执行
            try:
                result = js2py.eval_js(full_code)
                if result and isinstance(result, str):
                    # 检查是否是URL
                    if result.startswith('http'):
                        return True, result, ""
                    # 检查是否包含URL
                    url = JSRuleProcessor.extract_url_from_js(result, keyword, source_url)
                    if url:
                        return True, url, ""
            except Exception as e:
                logger.debug(f"JS 执行失败: {str(e)[:50]}")

            # 尝试直接提取 URL
            url = JSRuleProcessor.extract_url_from_js(js_code, keyword, source_url)
            if url:
                return True, url, ""

            return False, None, "无法解析JS代码"

        except ImportError:
            # js2py 未安装，尝试简单解析
            url = JSRuleProcessor.extract_url_from_js(js_code, keyword, source_url)
            if url:
                return True, url, ""
            return False, None, "JS引擎未安装"

        except Exception as e:
            logger.error(f"JS 处理异常: {str(e)[:50]}")
            return False, None, str(e)[:50]

    @staticmethod
    def parse_js_result(result: str) -> Tuple[str, str, Optional[str]]:
        """
        解析 JS 执行结果

        Args:
            result: JS 执行结果字符串

        Returns:
            (URL, 方法, POST数据)
        """
        if not result:
            return "", "GET", None

        parts = result.split('|')
        url = parts[0] if parts else ""
        method = parts[1] if len(parts) > 1 else "GET"
        post_data = parts[2] if len(parts) > 2 else None

        return url, method, post_data

    @staticmethod
    def is_supported_js(js_code: str) -> bool:
        """
        检查 JS 代码是否可能被支持

        Args:
            js_code: JavaScript 代码

        Returns:
            是否可能支持
        """
        # 检查是否包含 HTTP URL
        if re.search(r'https?://', js_code):
            return True

        # 检查是否是简单的字符串操作
        simple_patterns = [
            r'["\'][^"\']*["\']\s*\+',  # 字符串拼接
            r'var\s+\w+\s*=',           # 变量声明
            r'Date\.now\(\)',           # 时间戳
            r'java\.md5Encode',         # MD5
            r'source\.key',             # 书源URL
            r'source\.getKey',          # 书源URL
            r'JSON\.stringify',         # JSON
        ]

        for pattern in simple_patterns:
            if re.search(pattern, js_code):
                return True

        return False

    @staticmethod
    def detect_unsupported_features(js_code: str) -> Optional[str]:
        """
        检测 JS 代码中不支持的功能

        Args:
            js_code: JavaScript 代码

        Returns:
            不支持的功能描述，如果没有则返回 None
        """
        # 检测不支持的加密方法
        encryption_patterns = [
            (r'HMacSHA256|HMACSHA256|hmacSha256', 'HMAC-SHA256加密'),
            (r'HMacSHA1|HMACSHA1', 'HMAC-SHA1加密'),
            (r'DES|DESede|Blowfish', 'DES/3DES加密'),
            (r'AES|AES/CBC|AES/ECB', 'AES加密'),
            (r'RSA|SHA256WithRSA', 'RSA加密'),
            (r'java\.webView', 'WebView动态渲染'),
            (r'java\.connect', '复杂网络请求'),
        ]

        for pattern, feature_name in encryption_patterns:
            if re.search(pattern, js_code, re.IGNORECASE):
                return f"不支持{feature_name}"

        return None