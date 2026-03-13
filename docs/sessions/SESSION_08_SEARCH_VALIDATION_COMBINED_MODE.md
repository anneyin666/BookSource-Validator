# SESSION_08 搜索校验功能

## 会话目标

新增并优化搜索校验功能：
1. 新增搜索校验功能（测试书源搜索/发现功能是否可用）
2. 支持选择"仅搜索"、"仅发现"或"搜索+发现"组合模式
3. 只校验有对应规则的书源
4. 失败按原因分组显示
5. 支持并发数和超时时间设置

## 完成任务

### 1. 搜索校验基础功能

| 功能 | 说明 |
|------|------|
| 校验类型 | 仅搜索 / 仅发现 / 搜索+发现 |
| 预设关键词 | 玄幻、重生、穿越 |
| 自定义关键词 | 用户可输入任意关键词 |
| 并发设置 | 1/4/8/16/32 线程可选 |
| 超时设置 | 15/30/45/60 秒可选 |
| 实时进度 | SSE 模式显示校验进度 |
| 结果展示 | 有效书源统计、失败分组 |

### 2. 书源规则支持

| 字段 | 说明 |
|------|------|
| `searchUrl` | 搜索URL模板，支持 `{{key}}` 占位符 |
| `exploreUrl` | 发现URL，支持多行分类格式 |

**URL模板格式**：
- `https://example.com/search?wd={{key}}` - 直接替换
- `{{key|encode}}` - URL编码后替换
- 支持 POST/GET 方法

### 3. 校验类型选项

| 选项 | 说明 |
|------|------|
| 🔍 仅搜索 | 只校验有 `searchUrl` 规则的书源 |
| 📚 仅发现 | 只校验有 `exploreUrl` 规则的书源 |
| 🔍📚 搜索+发现 | 校验有任一规则的书源，至少一个通过即有效 |

**代码位置**：[SearchValidator.vue:9-27](../frontend/src/components/SearchValidator.vue#L9-L27)

```vue
<div class="validate-type">
  <span class="type-label">校验类型：</span>
  <button :class="['type-btn', { active: validateType === 'search' }]" @click="validateType = 'search'">
    🔍 仅搜索
  </button>
  <button :class="['type-btn', { active: validateType === 'explore' }]" @click="validateType = 'explore'">
    📚 仅发现
  </button>
  <button :class="['type-btn', { active: validateType === 'both' }]" @click="validateType = 'both'">
    🔍📚 搜索+发现
  </button>
</div>
```

### 4. 后端组合模式逻辑

| 功能 | 说明 |
|------|------|
| 规则检查 | 校验前检查书源是否有对应规则 |
| 跳过无规则 | 无规则书源直接标记失败，不发起请求 |
| 组合校验 | 同时校验搜索和发现，任一通过即有效 |
| 失败分组 | 按失败原因分组（如"搜索:超时; 发现:连接失败"） |

**代码位置**：[sources.py:838-234](../backend/app/api/sources.py#L838-L234)

#### 组合模式核心逻辑

```python
if validate_type == 'both':
    has_search = SearchValidatorService.has_search_rule(source)
    has_explore = SearchValidatorService.has_explore_rule(source)

    # 没有任何规则，跳过
    if not has_search and not has_explore:
        # 记录失败：无规则
        return

    # 校验搜索
    if has_search:
        search_valid, search_reason, _ = await SearchValidatorService.validate_search(...)

    # 校验发现
    if has_explore:
        explore_valid, explore_reason, _ = await SearchValidatorService.validate_explore(...)

    # 至少一个有效就算通过
    if search_valid or explore_valid:
        valid_sources.append(source)
    else:
        # 记录失败原因（组合格式）
        reasons = []
        if has_search and not search_valid:
            reasons.append(f"搜索:{search_reason}")
        if has_explore and not explore_valid:
            reasons.append(f"发现:{explore_reason}")
```

### 5. 单一模式规则检查

| 模式 | 规则检查 | 无规则处理 |
|------|----------|------------|
| 仅搜索 | `has_search_rule()` | 标记"无搜索规则" |
| 仅发现 | `has_explore_rule()` | 标记"无发现规则" |

避免对无规则书源发起无效请求。

### 6. 失败分组优化

失败原因格式：
- 单一模式：`超时`、`连接失败`、`HTTP 403`
- 组合模式：`搜索:超时; 发现:连接失败`

分组逻辑已在原有代码中实现，本次修改扩展支持组合原因格式。

### 7. 并发和超时设置

| 功能 | 说明 |
|------|------|
| 并发数选择 | 复用 ConcurrencySelector 组件 |
| 超时时间选择 | 复用 TimeoutSelector 组件 |
| 参数传递 | 通过 emit 事件传递给父组件 |

**代码位置**：[SearchValidator.vue:53-56](../frontend/src/components/SearchValidator.vue#L53-L56)

```vue
<!-- 参数设置 -->
<div class="settings-row">
  <ConcurrencySelector v-model="concurrency" />
  <TimeoutSelector v-model="timeout" />
</div>
```

**参数传递**：

```javascript
// 开始校验
function startValidation() {
  emit('start-validation', {
    validateType: validateType.value,
    keyword: keyword.value,
    concurrency: concurrency.value,
    timeout: timeout.value
  })
}
```

## 技术决策

### 校验策略

1. **规则优先**：先检查规则再校验，避免无效请求
2. **宽松组合**：组合模式下任一通过即有效
3. **详细原因**：组合模式失败原因包含具体哪个校验失败

### 性能优化

- 无规则书源直接跳过，减少网络请求
- 并发校验保持不变，由 semaphore 控制

## API 接口

| 接口 | 说明 |
|------|------|
| `POST /api/validate/search/start` | 开始搜索校验（SSE模式） |
| `GET /api/validate/search/progress/{session_id}` | SSE进度推送 |

## 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/services/search_validator.py` | 新建 | 搜索校验服务 |
| `backend/app/api/sources.py` | 修改 | 搜索校验SSE接口、组合模式逻辑 |
| `backend/app/services/session_manager.py` | 修改 | 搜索校验额外字段 |
| `frontend/src/components/SearchValidator.vue` | 新建 | 搜索校验UI组件 |
| `frontend/src/api/sources.js` | 修改 | startSearchValidation函数 |
| `frontend/src/App.vue` | 修改 | 搜索校验模式集成 |

## 测试结果

```
37 passed in 1.55s
```

所有测试通过。

## 功能验证清单

| # | 功能 | 状态 |
|---|------|------|
| 1 | 仅搜索模式 | ✅ |
| 2 | 仅发现模式 | ✅ |
| 3 | 搜索+发现组合模式 | ✅ |
| 4 | 无规则书源跳过 | ✅ |
| 5 | 失败按原因分组 | ✅ |
| 6 | 预设关键词选择 | ✅ |
| 7 | 自定义关键词输入 | ✅ |
| 8 | SSE实时进度 | ✅ |
| 9 | 并发数设置 | ✅ |
| 10 | 超时时间设置 | ✅ |

## 使用说明

### 搜索校验模式

1. 切换到「搜索校验」标签
2. 上传书源JSON文件
3. 选择校验类型：
   - **仅搜索**：只测试搜索功能，使用预设或自定义关键词
   - **仅发现**：只测试发现功能
   - **搜索+发现**：同时测试两个功能，任一有效即通过
4. 选择或输入搜索关键词（搜索模式或组合模式显示）
5. 设置并发数和超时时间
6. 点击「开始校验」
7. 查看校验进度和结果
8. 下载有效书源或查看失败分组

## 后续建议

### 功能增强

1. **搜索结果预览**
   - 显示搜索到的书籍列表预览
   - 支持点击书名查看详情

2. **发现分类选择**
   - 解析发现URL的分类列表
   - 允许用户选择特定分类进行校验

3. **智能关键词推荐**
   - 根据书源类型推荐合适的搜索关键词
   - 支持从书源名称提取关键词

### 性能优化

1. **请求优化**
   - 添加请求去重，避免重复请求同一URL
   - 支持 HTTP/2 多路复用

2. **结果缓存**
   - 缓存已校验的书源结果
   - 支持断点续传

### 用户体验

1. **校验报告**
   - 生成详细的校验报告（PDF/HTML）
   - 支持分享校验结果链接

2. **书源评分**
   - 根据搜索/发现功能可用性计算书源评分
   - 按评分排序下载结果

---

**会话日期**：2026-03-13
**版本**：v1.8.0