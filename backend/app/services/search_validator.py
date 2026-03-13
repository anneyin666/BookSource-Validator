# 搜索校验服务
import re
import json
import logging
import asyncio
from typing import List, Dict, Tuple, Optional
from urllib.parse import quote
import httpx

from app.services.js_processor import JSRuleProcessor

logger = logging.getLogger(__name__)


class SearchValidatorService:
    """搜索校验服务 - 测试书源的搜索和发现功能"""

    # 预设搜索关键词
    PRESET_KEYWORDS = ['玄幻', '重生', '穿越']

    # 手机端请求头
    MOBILE_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    @staticmethod
    def get_search_url(source: dict) -> Optional[str]:
        """获取书源的搜索URL模板"""
        # 支持两种字段名
        search_url = source.get('searchUrl', '') or source.get('searchURL', '')
        if not search_url:
            return None
        return search_url

    @staticmethod
    def get_explore_url(source: dict) -> Optional[str]:
        """获取书源的发现URL"""
        explore_url = source.get('exploreUrl', '') or source.get('exploreURL', '')
        if not explore_url:
            return None
        return explore_url

    @staticmethod
    def has_search_rule(source: dict) -> bool:
        """检查书源是否有搜索规则"""
        search_url = SearchValidatorService.get_search_url(source)
        if not search_url:
            return False
        # 检查是否有搜索列表规则
        search_list = source.get('searchList', '') or source.get('ruleSearch', {}).get('bookList', '')
        return bool(search_list) or True  # 即使没有规则也尝试校验

    @staticmethod
    def has_explore_rule(source: dict) -> bool:
        """检查书源是否有发现规则"""
        explore_url = SearchValidatorService.get_explore_url(source)
        return bool(explore_url)

    @staticmethod
    def build_search_request(search_url: str, keyword: str, base_url: str = "") -> Tuple[str, str, dict]:
        """
        构建搜索请求

        支持的URL模板格式：
        - {{key}} - 直接替换
        - {{key|encode}} - URL编码后替换
        - {key} - 直接替换
        - POST格式: url,{"method":"POST","body":"key={{key}}"}
        - 带规则格式: url@get->{{rule}} (提取URL部分)
        - 多行格式: 第一行URL，后续JSON配置

        Args:
            search_url: 搜索URL模板
            keyword: 搜索关键词
            base_url: 书源基础URL（用于补全相对URL）

        Returns:
            (实际请求URL, 请求方法, POST数据)
        """
        url = search_url
        method = "GET"
        post_data = None
        custom_headers = {}

        # 编码关键词
        encoded_keyword = quote(keyword, safe='')

        # 1. 处理带规则的URL格式 (url@get->{{rule}} 或 url@post->{{rule}})
        if '@' in url:
            # 提取URL部分（@之前）
            at_index = url.find('@')
            url = url[:at_index]

        # 2. 处理多行格式或JSON配置格式
        # 格式: url,{"method":"POST","body":"xxx"} 或 url\n{"method":"POST"}
        json_config = None
        if '\n' in url:
            # 多行格式：URL在第一行，JSON配置在后续行
            lines = url.split('\n')
            first_line = lines[0].strip()

            # 检查第一行是否以 ,{ 结尾（表示 JSON 配置开始）
            if first_line.endswith(',{'):
                # URL 是第一行去掉 ,{ 的部分
                url = first_line[:-2]
                # JSON 配置需要包含被去掉的 {
                json_str = '{' + '\n'.join(lines[1:])
            else:
                url = first_line
                # JSON 配置从第二行开始
                json_str = '\n'.join(lines[1:])

            if json_str.strip():
                try:
                    json_config = json.loads(json_str)
                except:
                    pass
        elif ',{' in url or '{"' in url:
            # URL后跟JSON配置
            # 查找JSON开始的索引
            json_start = url.find('{')
            if json_start > 0:
                json_str = url[json_start:]
                url = url[:json_start].rstrip(',')
                try:
                    json_config = json.loads(json_str)
                except:
                    pass

        # 3. 从JSON配置中提取方法和数据
        if json_config:
            method = json_config.get('method', 'GET').upper()
            if 'body' in json_config:
                post_data = json_config['body']
            if 'headers' in json_config:
                custom_headers = json_config['headers']

        # 4. 替换模板变量
        # {{key|encode}} 格式 - URL编码
        url = re.sub(r'\{\{key\|encode\}\}', encoded_keyword, url)
        # {{key}} 格式 - 直接替换
        url = url.replace('{{key}}', keyword)
        # {key} 格式 - 直接替换
        url = url.replace('{key}', keyword)

        # 替换POST数据中的变量
        if post_data:
            post_data = re.sub(r'\{\{key\|encode\}\}', encoded_keyword, post_data)
            post_data = post_data.replace('{{key}}', keyword)
            post_data = post_data.replace('{key}', keyword)

        # 5. 处理其他未替换的变量
        if '{{' in url or '{' in url:
            url = re.sub(r'\{\{[^}]+\}\}', keyword, url)
            url = re.sub(r'\{[^}]+\}', keyword, url)

        if post_data and ('{{' in post_data or '{' in post_data):
            post_data = re.sub(r'\{\{[^}]+\}\}', keyword, post_data)
            post_data = re.sub(r'\{[^}]+\}', keyword, post_data)

        # 6. 修复URL前缀 - 如果URL不以http开头，尝试补全
        if not url.startswith(('http://', 'https://')):
            # 从书源基础URL获取域名
            if base_url and base_url.startswith(('http://', 'https://')):
                from urllib.parse import urlparse
                parsed = urlparse(base_url)
                if parsed.netloc:
                    if url.startswith('/'):
                        url = f"{parsed.scheme}://{parsed.netloc}{url}"
                    else:
                        url = f"{parsed.scheme}://{parsed.netloc}/{url}"
                else:
                    url = "https://" + url
            else:
                url = "https://" + url

        # 7. 清理URL中的多余字符
        url = url.strip().rstrip(',')

        return url, method, post_data

    @staticmethod
    def check_search_results(content: str, source: dict) -> Tuple[bool, int]:
        """
        检查搜索结果是否有效

        Args:
            content: 响应内容
            source: 书源对象

        Returns:
            (是否有效, 结果数量)
        """
        # 尝试解析JSON
        try:
            data = json.loads(content)

            # 检查常见的数据结构
            if isinstance(data, list):
                return len(data) > 0, len(data)

            if isinstance(data, dict):
                # 检查常见的响应格式
                for key in ['data', 'result', 'results', 'books', 'list', 'items',
                            'bookList', 'booklist', 'BookList', 'book_list', 'booklist',
                            'dataList', 'datas', 'rows', 'records', 'itemsList']:
                    if key in data:
                        value = data[key]
                        if isinstance(value, list):
                            return len(value) > 0, len(value)
                        elif isinstance(value, dict):
                            # 嵌套结构，继续查找
                            for sub_key in ['list', 'items', 'records', 'data', 'rows']:
                                if sub_key in value and isinstance(value[sub_key], list):
                                    return len(value[sub_key]) > 0, len(value[sub_key])

                # 检查是否有分页结构
                if 'records' in data:
                    records = data['records']
                    if isinstance(records, list):
                        return len(records) > 0, len(records)

                # 检查 data.data 结构
                if 'data' in data and isinstance(data['data'], dict):
                    inner_data = data['data']
                    for key in ['list', 'items', 'records', 'books', 'rows']:
                        if key in inner_data and isinstance(inner_data[key], list):
                            return len(inner_data[key]) > 0, len(inner_data[key])

                # 检查是否有 success/ok 状态
                if data.get('success') or data.get('ok') or data.get('status') == 'ok':
                    return True, 0

                # 检查错误码 - 只有明确的错误才返回失败
                if 'code' in data:
                    code = data.get('code')
                    if code in [0, 200, '0', '200', 'success', 1, '1']:
                        return True, 0
                    # 其他错误码
                    if code in [-1, 404, 500, 'error', 'fail']:
                        return False, 0

                # 检查 msg/message 字段
                msg = data.get('msg', '') or data.get('message', '')
                if msg and ('成功' in msg or 'success' in msg.lower()):
                    return True, 0
                if msg and ('失败' in msg or 'error' in msg.lower() or '无' in msg):
                    return False, 0

                # 检查响应内容长度 - 如果JSON对象有很多字段，可能包含数据
                if len(data) > 3:
                    # 没有明显的错误标记，假设可能有效
                    return True, 0

                return False, 0

        except json.JSONDecodeError:
            pass

        # HTML响应 - 根据内容长度判断
        # 有足够的内容可能有效
        if len(content) > 500:
            # 检查是否有常见的"无结果"标记
            no_result_patterns = [
                '没有找到', '无结果', '暂无数据', '没有相关', '未找到',
                '搜索无结果', '没有搜到', '找不到', '不存在',
                'not found', 'no result', 'empty', 'no data', 'no matches'
            ]
            content_lower = content.lower()
            for pattern in no_result_patterns:
                if pattern in content_lower:
                    return False, 0

            # 检查是否有书籍列表的常见标记
            book_patterns = [
                'book', '小说', '章节', '作者', 'author', 'chapter',
                'bookname', 'bookname', 'articlename', 'novel',
                '书籍', '书名', '最新章节', '阅读'
            ]
            for pattern in book_patterns:
                if pattern in content_lower:
                    return True, 0

            # 检查是否有列表结构的 HTML 标签
            list_patterns = ['<li', '<div class="item', '<tr', '<dd']
            for pattern in list_patterns:
                if pattern in content_lower:
                    return True, 0

            # 内容足够长，假设有效
            return True, 0

        # 内容太短，可能是空响应
        if len(content) < 100:
            return False, 0

        # 中等长度内容，假设有效
        return True, 0

    @staticmethod
    async def validate_search(
        source: dict,
        keyword: str,
        timeout: int = 30
    ) -> Tuple[bool, str, Optional[List[dict]]]:
        """
        验证书源的搜索功能

        Args:
            source: 书源对象
            keyword: 搜索关键词
            timeout: 超时时间

        Returns:
            (是否成功, 失败原因, 搜索结果列表)
        """
        search_url = SearchValidatorService.get_search_url(source)
        if not search_url:
            return False, "无搜索规则", None

        # 获取书源基础URL用于补全相对路径
        base_url = source.get('bookSourceUrl', '')

        # 清理 base_url 中的中文字符（如作者信息）
        chinese_match = re.search(r'[\u4e00-\u9fff]', base_url)
        if chinese_match:
            chinese_index = chinese_match.start()
            slash_index = base_url.find('/', 8)  # 跳过 http:// 或 https://
            if slash_index != -1 and chinese_index > slash_index:
                base_url = base_url[:chinese_index]
            elif chinese_index > 8:
                base_url = base_url[:chinese_index]

        # 检查是否包含 JavaScript 规则
        if '@js:' in search_url or 'javascript:' in search_url.lower():
            # 尝试处理 JS 规则
            js_code = search_url
            if '@js:' in js_code:
                js_code = js_code.split('@js:')[1]

            # 移除 {{cookie.removeCookie 等前缀
            if js_code.startswith('{{'):
                # 找到 @js: 后面的代码
                if '@js:' in search_url:
                    js_code = search_url.split('@js:')[-1]

            # 尝试执行 JS 代码提取 URL
            success, result_url, error = JSRuleProcessor.try_execute_js(js_code, keyword, base_url)
            if success and result_url:
                # 解析结果
                url, method, post_data = JSRuleProcessor.parse_js_result(result_url)
                if not url:
                    url = result_url
                    method = "GET"
                    post_data = None
            else:
                # JS 解析失败，标记原因
                error_msg = error[:30] if error else "JS解析失败"
                return False, error_msg, None
        else:
            url, method, post_data = SearchValidatorService.build_search_request(search_url, keyword, base_url)

        # 检查 URL 是否有效
        if not url or not url.startswith(('http://', 'https://')):
            return False, "URL格式错误", None

        # 最多重试2次
        max_retries = 2
        last_error = ""

        for attempt in range(max_retries):
            try:
                # 第二次重试时强制使用 HTTP/1.1
                use_http1 = attempt > 0
                async with httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=True,
                    verify=False,
                    http2=not use_http1,  # 第二次禁用 HTTP/2
                    http1=True
                ) as client:
                    headers = dict(SearchValidatorService.MOBILE_HEADERS)
                    # 添加书源自定义请求头
                    if source.get('header'):
                        try:
                            custom_headers = json.loads(source['header'])
                            headers.update(custom_headers)
                        except:
                            pass

                    if method == "POST":
                        response = await client.post(url, data=post_data, headers=headers)
                    else:
                        response = await client.get(url, headers=headers)

                    if response.status_code == 403:
                        # Cloudflare 防护，视为成功
                        return True, "", []

                    if not (200 <= response.status_code < 400):
                        return False, f"HTTP {response.status_code}", None

                    content = response.text
                    is_valid, count = SearchValidatorService.check_search_results(content, source)

                    if is_valid:
                        return True, "", []
                    else:
                        return False, "搜索无结果", None

            except httpx.TimeoutException:
                last_error = "超时"
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except httpx.ConnectError:
                last_error = "连接失败"
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except httpx.ConnectTimeout:
                last_error = "连接超时"
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except httpx.ReadTimeout:
                last_error = "读取超时"
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except httpx.WriteTimeout:
                last_error = "写入超时"
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except httpx.RemoteProtocolError as e:
                # HTTP 协议错误（如 Server disconnected）- 重试
                error_msg = str(e)[:50]
                if 'disconnected' in error_msg.lower():
                    last_error = "服务器断开"
                else:
                    last_error = "协议错误"
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except httpx.HTTPStatusError as e:
                return False, f"HTTP {e.response.status_code}", None
            except httpx.RequestError as e:
                # 捕获所有 httpx 网络错误（包括 SSL 错误）
                error_msg = str(e)[:50] if str(e) else type(e).__name__
                if 'ssl' in error_msg.lower() or 'certificate' in error_msg.lower():
                    last_error = "SSL错误"
                elif not error_msg:
                    last_error = "网络错误"
                else:
                    last_error = error_msg
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except Exception as e:
                error_msg = str(e)[:50]
                logger.error(f"搜索校验异常 [{url}]: {error_msg}")
                last_error = error_msg
                break

        return False, last_error if last_error else "未知错误", None

    @staticmethod
    async def validate_explore(
        source: dict,
        timeout: int = 30
    ) -> Tuple[bool, str, Optional[List[dict]]]:
        """
        验证书源的发现功能

        Args:
            source: 书源对象
            timeout: 超时时间

        Returns:
            (是否成功, 失败原因, 发现结果列表)
        """
        explore_url = SearchValidatorService.get_explore_url(source)
        if not explore_url:
            return False, "无发现规则", None

        # 处理发现URL - 可能是多行的分类URL
        urls = []
        for line in explore_url.split('\n'):
            line = line.strip()
            if line and '::' in line:
                # 格式: 分类名::URL
                parts = line.split('::', 1)
                if len(parts) == 2:
                    urls.append((parts[0], parts[1]))
            elif line.startswith('http'):
                urls.append(('', line))

        if not urls:
            if explore_url.startswith('http'):
                urls.append(('', explore_url))
            else:
                return False, "无效发现URL", None

        # 只测试第一个URL
        name, url = urls[0]

        # 修复URL前缀 - 如果URL不以http开头，尝试补全
        if not url.startswith(('http://', 'https://')):
            base_url = source.get('bookSourceUrl', '')

            # 清理 base_url 中的中文字符（如作者信息）
            chinese_match = re.search(r'[\u4e00-\u9fff]', base_url)
            if chinese_match:
                chinese_index = chinese_match.start()
                slash_index = base_url.find('/', 8)  # 跳过 http:// 或 https://
                if slash_index != -1 and chinese_index > slash_index:
                    base_url = base_url[:chinese_index]
                elif chinese_index > 8:
                    base_url = base_url[:chinese_index]

            if base_url and base_url.startswith(('http://', 'https://')):
                from urllib.parse import urlparse
                parsed = urlparse(base_url)
                if parsed.netloc:
                    if url.startswith('/'):
                        url = f"{parsed.scheme}://{parsed.netloc}{url}"
                    else:
                        url = f"{parsed.scheme}://{parsed.netloc}/{url}"
                else:
                    url = "https://" + url
            else:
                url = "https://" + url

        # 最多重试2次
        max_retries = 2
        last_error = ""

        for attempt in range(max_retries):
            try:
                # 第二次重试时强制使用 HTTP/1.1
                use_http1 = attempt > 0
                async with httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=True,
                    verify=False,
                    http2=not use_http1,
                    http1=True
                ) as client:
                    headers = dict(SearchValidatorService.MOBILE_HEADERS)
                    if source.get('header'):
                        try:
                            custom_headers = json.loads(source['header'])
                            headers.update(custom_headers)
                        except:
                            pass

                    response = await client.get(url, headers=headers)

                    if response.status_code == 403:
                        return True, "", []

                    if not (200 <= response.status_code < 400):
                        return False, f"HTTP {response.status_code}", None

                    content = response.text
                    is_valid, count = SearchValidatorService.check_search_results(content, source)

                    if is_valid:
                        return True, "", []
                    else:
                        return False, "发现无结果", None

            except httpx.TimeoutException:
                last_error = "超时"
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except httpx.ConnectError:
                last_error = "连接失败"
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except httpx.ConnectTimeout:
                last_error = "连接超时"
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except httpx.ReadTimeout:
                last_error = "读取超时"
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except httpx.WriteTimeout:
                last_error = "写入超时"
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except httpx.RemoteProtocolError as e:
                error_msg = str(e)[:50]
                if 'disconnected' in error_msg.lower():
                    last_error = "服务器断开"
                else:
                    last_error = "协议错误"
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except httpx.HTTPStatusError as e:
                return False, f"HTTP {e.response.status_code}", None
            except httpx.RequestError as e:
                error_msg = str(e)[:50] if str(e) else type(e).__name__
                if 'ssl' in error_msg.lower() or 'certificate' in error_msg.lower():
                    last_error = "SSL错误"
                elif not error_msg:
                    last_error = "网络错误"
                else:
                    last_error = error_msg
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except Exception as e:
                error_msg = str(e)[:50]
                logger.error(f"发现校验异常 [{url}]: {error_msg}")
                last_error = error_msg
                break

        return False, last_error if last_error else "未知错误", None

    @staticmethod
    async def batch_validate_search(
        sources: List[dict],
        keyword: str,
        validate_type: str = 'search',
        timeout: int = 30,
        concurrency: int = 16,
        progress_callback=None
    ) -> Tuple[List[dict], Dict[str, List[dict]]]:
        """
        批量搜索校验

        Args:
            sources: 书源列表
            keyword: 搜索关键词（search模式使用）
            validate_type: 校验类型 'search' 或 'explore'
            timeout: 超时时间
            concurrency: 并发数
            progress_callback: 进度回调函数

        Returns:
            (成功的书源列表, 失败分组)
        """
        import asyncio

        # 先过滤有对应规则的书源
        if validate_type == 'search':
            valid_sources_to_check = [s for s in sources if SearchValidatorService.has_search_rule(s)]
        else:
            valid_sources_to_check = [s for s in sources if SearchValidatorService.has_explore_rule(s)]

        if not valid_sources_to_check:
            return [], {"无规则": [{'url': '', 'name': s.get('bookSourceName', ''), 'reason': '无规则'} for s in sources]}

        valid_sources = []
        failed_sources = {}
        semaphore = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()
        processed = 0

        async def validate_single(source):
            nonlocal processed, valid_sources, failed_sources

            async with semaphore:
                url = source.get('bookSourceUrl', '')
                name = source.get('bookSourceName', '')

                if validate_type == 'search':
                    is_valid, reason, results = await SearchValidatorService.validate_search(
                        source, keyword, timeout
                    )
                else:
                    is_valid, reason, results = await SearchValidatorService.validate_explore(
                        source, timeout
                    )

                async with lock:
                    processed += 1
                    if is_valid:
                        valid_sources.append(source)
                    else:
                        if reason not in failed_sources:
                            failed_sources[reason] = []
                        failed_sources[reason].append({
                            'url': url,
                            'name': name,
                            'reason': reason
                        })

                    if progress_callback:
                        progress_callback(processed, len(valid_sources_to_check), url, len(valid_sources), len(failed_sources))

        tasks = [validate_single(s) for s in valid_sources_to_check]
        await asyncio.gather(*tasks)

        return valid_sources, failed_sources


# ===================== 错误分类工具 =====================

# 错误分类定义
ERROR_CATEGORIES = {
    'fixable': {
        'name': '可修复',
        'icon': '🔄',
        'hint': '这些书源可能因网络问题暂时失效，可稍后重试',
        'keywords': ['超时', '连接失败', '连接超时', 'SSL错误', '读取超时', '写入超时',
                     '服务器断开', '协议错误', '网络错误', '连接被拒', 'DNS']
    },
    'unfixable': {
        'name': '不可修复',
        'icon': '❌',
        'hint': '这些书源规则有问题或使用了不支持的加密',
        'keywords': ['无搜索规则', '无发现规则', 'URL格式错误', '无效发现URL',
                     '不支持', '无法解析JS', 'JS解析失败', '加密']
    },
    'checkable': {
        'name': '需检查',
        'icon': '⚠️',
        'hint': '这些书源可能已下线或内容有变化',
        'keywords': ['HTTP 404', 'HTTP 403', 'HTTP 500', 'HTTP 502', 'HTTP 503',
                     '搜索无结果', '发现无结果', '未知错误']
    }
}


def categorize_error(reason: str) -> str:
    """
    将错误原因分类

    Args:
        reason: 错误原因字符串

    Returns:
        分类标识: 'fixable', 'unfixable', 或 'checkable'
    """
    for category, info in ERROR_CATEGORIES.items():
        for keyword in info['keywords']:
            if keyword in reason:
                return category
    return 'checkable'  # 默认归类为需检查


def categorize_failed_sources(failed_groups: list) -> dict:
    """
    将失败书源按分类整理

    Args:
        failed_groups: 失败书源分组列表 [{'reason': '错误原因', 'sources': [...]}]

    Returns:
        分类后的失败书源 {'fixable': [...], 'unfixable': [...], 'checkable': [...]}
    """
    categorized = {
        'fixable': [],
        'unfixable': [],
        'checkable': []
    }

    for group in failed_groups:
        reason = group.get('reason', '未知错误')
        category = categorize_error(reason)

        for source in group.get('sources', []):
            # 统一数据格式，确保有 name 和 reason 字段
            # 深度校验使用 name/reason，搜索校验使用 bookSourceName/_failureReason
            display_name = (
                source.get('name') or
                source.get('bookSourceName') or
                '未知书源'
            )
            display_reason = (
                source.get('reason') or
                source.get('_failureReason') or
                reason
            )

            categorized[category].append({
                'url': source.get('url') or source.get('bookSourceUrl') or '',
                'name': display_name,
                'reason': display_reason,
                '_category': category,
                '_categoryName': ERROR_CATEGORIES[category]['name'],
                '_categoryIcon': ERROR_CATEGORIES[category]['icon']
            })

    return categorized


def get_error_category_info(category: str) -> dict:
    """获取错误分类信息"""
    return ERROR_CATEGORIES.get(category, ERROR_CATEGORIES['checkable'])