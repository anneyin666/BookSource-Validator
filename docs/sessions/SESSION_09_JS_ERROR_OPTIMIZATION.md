# SESSION_09 搜索校验错误提示优化

## 会话目标

修复搜索校验中"空白"失败原因问题，优化 JS 规则解析错误提示。

---

## 完成任务

### 1. 修复"空白"失败原因问题

**问题描述：**
搜索校验后，部分失败书源的失败原因显示为空白，导致用户无法理解失败原因。

**问题原因：**
- `validate_search` 和 `validate_explore` 函数中 `last_error` 初始化为空字符串
- 当重试耗尽但未正确设置错误信息时，返回空的失败原因

**修复方案：**

| 文件 | 行号 | 修改内容 |
|------|------|----------|
| `search_validator.py` | 444 | `validate_search` 添加空错误回退 |
| `search_validator.py` | 592 | `validate_explore` 添加相同修复 |
| `sources.py` | 989-992 | 空 `search_reason`/`explore_reason` 显示"未知错误" |
| `App.vue` | 198 | 模板显示空原因回退为"未知错误" |
| `App.vue` | 1027 | 导出失败书源时空原因回退 |

**修复代码：**
```python
# search_validator.py
return False, last_error if last_error else "未知错误", None
```

```python
# sources.py - 失败原因拼接时处理空值
reasons.append(f"搜索:{search_reason if search_reason else '未知错误'}")
reasons.append(f"发现:{explore_reason if explore_reason else '未知错误'}")
```

### 2. 优化 JS 加密检测

**问题描述：**
部分书源使用复杂加密算法（HMAC-SHA256、DES、AES 等），Python 无法模拟阅读 App 的 Java 加密 API，导致解析失败且错误提示不明确。

**优化方案：**

新增 `detect_unsupported_features` 方法，提前检测不支持的加密功能：

| 加密/功能 | 检测关键词 |
|-----------|------------|
| HMAC-SHA256 | `HMacSHA256`, `HMACSHA256`, `hmacSha256` |
| HMAC-SHA1 | `HMacSHA1`, `HMACSHA1` |
| DES/3DES | `DES`, `DESede`, `Blowfish` |
| AES | `AES`, `AES/CBC`, `AES/ECB` |
| RSA | `RSA`, `SHA256WithRSA` |
| WebView | `java.webView` |
| 复杂网络 | `java.connect` |

**新增代码：**
```python
@staticmethod
def detect_unsupported_features(js_code: str) -> Optional[str]:
    """检测 JS 代码中不支持的功能"""
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
```

### 3. 搜索校验相对路径 URL 处理

**问题描述：**
部分书源的 `searchUrl` 使用相对路径，同时 `bookSourceUrl` 可能包含中文字符（如作者信息），导致 URL 解析失败。

**问题案例：**
| 书源 | bookSourceUrl | searchUrl | 错误 |
|------|---------------|-----------|------|
| ️笔趣阁 | `https://www.zw.com/作者名` | `modules/article/search.php?k={{key}}` | 未知错误 |
| ️萝莉文学 | `https://www.llwx.cc/` | `/search/,{"method":"POST",...}` | 协议错误 |

**修复方案：**

在 `validate_search` 和 `validate_explore` 函数中添加 `base_url` 中文字符清理：

```python
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
```

**修复位置：**
| 文件 | 行号 | 说明 |
|------|------|------|
| `search_validator.py` | 313-322 | `validate_search` 添加中文清理 |
| `search_validator.py` | 499-508 | `validate_explore` 添加中文清理 |

### 4. 多行 JSON 配置格式解析

**问题描述：**
部分书源的 `searchUrl` 使用多行 JSON 配置格式，但代码只解析第二行，导致 JSON 解析失败。

**问题案例：**
```
https://www.miaoquan2016.com/search/,{
  "body": "searchkey={{key}}&type=articlename",
  "charset": "UTF-8",
  "method": "POST"
}
```

**问题原因：**
原代码只解析 `lines[1]`，但 JSON 配置可能跨越多行。

**修复方案：**

```python
if '\n' in url:
    lines = url.split('\n')
    first_line = lines[0].strip()

    # 检查第一行是否以 ,{ 结尾（表示 JSON 配置开始）
    if first_line.endswith(',{'):
        url = first_line[:-2]
        json_str = '{' + '\n'.join(lines[1:])
    else:
        url = first_line
        json_str = '\n'.join(lines[1:])

    if json_str.strip():
        try:
            json_config = json.loads(json_str)
        except:
            pass
```

### 5. 正版网站域名过滤增强

**问题描述：**
原有的正版书籍过滤仅依赖 `bookSourceType=3` 和关键词"正版"/"官方"，无法识别实际的正版网站域名。

**修复方案：**

新增正版网站域名列表，通过 URL 匹配识别正版书源：

```python
# 正版网站域名列表
OFFICIAL_DOMAINS = {
    # 男频向
    'qidian.com', 'zongheng.com', 'chuangshi.qq.com', 'faloo.com',
    '17k.com', 'ciweimao.com', 'sfacg.com',
    # 女频向
    'jjwxc.net', 'hongxiu.com', 'xxsy.net', 'qdmm.com',
    'yunqi.qq.com', 'readnovel.com', 'xs8.cn', 'gongzicp.com',
    # 综合/免费平台
    'fanqienovel.com', 'qimao.com', 'zhangyue.com', 'book.qq.com',
    'read.douban.com', 'zhihu.com', 'tadu.com', 'zhulang.com',
    'shuhai.com', 'motie.com',
    # 电子书资源站
    'zxcs.info', 'jiumodiary.com',
}

# 支持子域名匹配（如 m.qidian.com, wap.qidian.com）
OFFICIAL_DOMAIN_PREFIXES = [
    'qidian', 'zongheng', 'chuangshi', 'faloo', '17k',
    'ciweimao', 'sfacg', 'jjwxc', 'hongxiu', 'xxsy',
    # ... 更多前缀
]
```

**识别逻辑：**
1. 检查 `bookSourceType` 是否为 3（正版）
2. 检查书源名称/备注是否包含"正版"/"官方"
3. **新增**：检查 `bookSourceUrl` 是否匹配正版网站域名

### 6. 无法支持的书源类型

以下书源因使用复杂加密算法或动态网络请求，Python 环境无法校验：

#### 3.1 实际测试案例分析

| 书源名称 | JS 特征 | 错误提示 | 原因 |
|----------|---------|----------|------|
| ❤️福书网 | `java.connect(url).raw().request().url()` | 不支持复杂网络请求 | 需要实际发起请求获取重定向URL |
| ❤️蛋文库 | `java.connect(url).raw().request().url()` | 不支持复杂网络请求 | 同上 |
| ❤️笔仙阁子🎃 | `java.connect(so).raw().request().url()` | 不支持复杂网络请求 | 同上 |
| 言情小说 | `java.connect` + `cookie.removeCookie` | 不支持复杂网络请求 | 需要动态请求+Cookie处理 |
| ❤️陶越文华 | 登录系统 + MD5签名 + 设备注册 | 无法解析JS代码 | 需要完整的Java运行环境 |
| ❤️爱淘小说 | `java.md5Encode().toUpperCase()` + 签名 | 不支持复杂网络请求 | 需要MD5签名+动态请求 |

#### 3.2 java.connect 代码示例

```javascript
// 典型的 java.connect 用法（无法模拟）
// 目的：获取 POST 请求重定向后的实际 URL
let url = source.getKey()+'/e/search/index.php,'+JSON.stringify({
  "method":"POST",
  "body":"keyboard="+key+"&show=title"
});
return java.put('surl', String(java.connect(url).raw().request().url()));
```

**问题分析：**
- `java.connect` 需要实际发起 HTTP 请求
- `.raw().request().url()` 获取重定向后的最终 URL
- Python 环境无法模拟阅读 App 的 Java 网络层

#### 3.3 签名验证示例

```javascript
// 陶越文华的签名逻辑（无法模拟）
pm.sign = java.md5Encode(spm + "&key=qcbook_123456");
// 还需要设备注册、token 获取等完整流程
```

**问题分析：**
- 需要完整的登录流程（设备注册、获取token）
- 签名验证依赖 App 端的密钥
- 即使能计算签名，也无法模拟完整的会话状态

---

## 技术决策

### 1. 空错误回退策略

**选择：** 在返回前检查空值，使用"未知错误"作为默认值

**理由：**
- 用户看到"未知错误"比空白更有信息量
- 保持错误提示的一致性
- 便于调试和问题追踪

### 2. 加密检测时机

**选择：** 在 JS 执行前检测不支持的加密功能

**理由：**
- 提前返回明确的错误信息
- 避免不必要的 JS 解析尝试
- 减少日志噪音

### 3. 不支持功能的处理

**选择：** 明确告知用户不支持的原因，而非尝试执行后失败

**理由：**
- 提供更好的用户体验
- 用户可以手动过滤这些书源
- 保持代码简洁

---

## 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/services/search_validator.py` | 修改 | 添加空错误回退、中文URL清理、多行JSON解析 |
| `backend/app/api/sources.py` | 修改 | 处理空失败原因 |
| `backend/app/services/js_processor.py` | 修改 | 新增加密检测方法 |
| `backend/app/services/filter.py` | 修改 | 新增正版网站域名过滤 |
| `backend/tests/test_search_validator.py` | 新建 | 搜索校验测试用例 |
| `backend/tests/test_filter.py` | 修改 | 新增正版域名过滤测试 |
| `frontend/src/App.vue` | 修改 | 前端空原因回退显示 |

---

## 测试结果

### Python 语法检查
```
Python syntax OK
```

### 单元测试
```
55 passed in 1.62s
```

### 新增测试用例
```
tests/test_search_validator.py::TestSearchValidatorService::test_build_search_request_direct_url PASSED
tests/test_search_validator.py::TestSearchValidatorService::test_build_search_request_with_encode PASSED
tests/test_search_validator.py::TestSearchValidatorService::test_build_search_request_post_format PASSED
tests/test_search_validator.py::TestSearchValidatorService::test_build_search_request_relative_path PASSED
tests/test_search_validator.py::TestSearchValidatorService::test_build_search_request_relative_path_with_leading_slash PASSED
tests/test_search_validator.py::TestSearchValidatorService::test_build_search_request_relative_path_post PASSED
tests/test_search_validator.py::TestSearchValidatorService::test_build_search_request_base_url_with_chinese PASSED
tests/test_search_validator.py::TestSearchValidatorService::test_build_search_request_multiline_json PASSED
tests/test_search_validator.py::TestSearchValidatorService::test_build_search_request_json_with_charset PASSED
tests/test_search_validator.py::TestSearchValidatorService::test_has_search_rule_with_searchurl PASSED
tests/test_search_validator.py::TestSearchValidatorService::test_has_search_rule_without_searchurl PASSED
tests/test_search_validator.py::TestSearchValidatorService::test_has_explore_rule_with_exploreurl PASSED
tests/test_search_validator.py::TestSearchValidatorService::test_has_explore_rule_without_exploreurl PASSED
```

### 前端构建
```
✓ built in 11.37s
```

### 加密检测测试
```
PASS: java.webView... -> 不支持WebView动态渲染
PASS: HMacSHA256.encrypt -> 不支持HMAC-SHA256加密
PASS: AES/CBC/PKCS5Padding -> 不支持AES加密
PASS: DES.decrypt -> 不支持DES/3DES加密
PASS: https://example.com/search?q=test -> None
```

---

## 功能验证清单

- [x] "空白"失败原因显示为"未知错误"
- [x] 搜索校验空原因正确处理
- [x] 发现校验空原因正确处理
- [x] 失败书源导出包含正确的失败原因
- [x] JS 加密检测功能正常工作
- [x] 前端显示正确的错误信息
- [x] 相对路径 searchUrl 正确补全
- [x] POST 格式相对路径正确处理
- [x] base_url 中文字符正确清理
- [x] 多行 JSON 配置格式正确解析
- [x] ,{ 结尾的多行格式正确处理
- [x] 正版网站域名识别过滤

---

## 使用说明

### 错误提示改进

搜索校验完成后，失败书源分析现在会显示明确的失败原因：

- **之前：** 空白（无法理解失败原因）
- **之后：** "未知错误"或其他具体原因

### 不支持的加密提示

对于使用复杂加密的书源，会显示具体的不支持原因：

- "不支持HMAC-SHA256加密"
- "不支持AES加密"
- "不支持DES/3DES加密"
- "不支持WebView动态渲染"

---

## 后续建议

### 功能增强
1. **加密模拟支持** - 考虑使用 Python 加密库模拟部分 Java 加密方法
2. **WebView 替代方案** - 研究 headless browser 替代方案

### 性能优化
1. **JS 解析缓存** - 缓存已解析的 JS 规则结果
2. **并行加密检测** - 批量检测时并行处理

### 用户体验
1. **错误分类** - 将错误分为"可修复"和"不可修复"两类
2. **建议提示** - 对可修复的错误提供修复建议

---

文档版本：v1.4
创建日期：2026-03-13
更新日期：2026-03-13