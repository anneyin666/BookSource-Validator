// 失败书源重试组合式函数
// 提供失败分组筛选、失败书源归一化与重试结果合并的纯逻辑。

// 旧数据兜底：失败原因中文关键词匹配
const NETWORK_RETRY_KEYWORDS = [
  '超时', '连接失败', '连接超时', '读取错误', '写入错误',
  '读取超时', '写入超时', '网络错误', 'SSL', '服务器断开', '协议错误'
]

export function useFailedRetry() {
  function isNetworkRetryReason(reason) {
    return NETWORK_RETRY_KEYWORDS.some((keyword) =>
      String(reason || '').includes(keyword)
    )
  }

  // 优先使用后端返回的失败分类；旧数据回退到关键词匹配
  function isRetryableGroup(group) {
    if (group?.category) {
      return group.category === 'fixable'
    }
    return isNetworkRetryReason(group?.reason)
  }

  function normalizeFailedSource(source) {
    const bookSourceUrl = source.bookSourceUrl || source.url || ''
    if (!bookSourceUrl) return null
    return {
      ...source,
      bookSourceUrl,
      bookSourceName: source.bookSourceName || source.name || '未命名'
    }
  }

  /**
   * 收集需要重试的失败书源
   * @param {Object} sourceData 当前结果数据
   * @param {boolean} onlyNetwork 是否只重试网络类失败
   */
  function collectFailedSources(sourceData, onlyNetwork) {
    const groups = sourceData?.failedGroups || []
    const retrySources = []
    const skippedGroups = []

    for (const group of groups) {
      const shouldRetry = !onlyNetwork || isRetryableGroup(group)
      if (!shouldRetry) {
        skippedGroups.push(group)
        continue
      }

      for (const source of group.sources || []) {
        const normalized = normalizeFailedSource(source)
        if (normalized) retrySources.push(normalized)
      }
    }

    return { retrySources, skippedGroups }
  }

  /**
   * 将重试结果合并回原有结果
   * @param {Object} previous 重试前的结果数据
   * @param {Object} data 重试结果接口数据
   * @param {Array} skippedGroups 未参与重试的失败分组
   */
  function mergeRetryResultData(previous, data, skippedGroups = []) {
    if (!previous) return null

    const sourceMap = new Map()
    for (const source of previous.dedupedSources || []) {
      const url = source.bookSourceUrl || source.url
      if (url) sourceMap.set(url, source)
    }
    for (const source of data.validSources || []) {
      const url = source.bookSourceUrl || source.url
      if (url) sourceMap.set(url, source)
    }

    const failedGroups = [
      ...(data.failedGroups || []),
      ...skippedGroups
    ].filter((group) => group.count > 0)
    const failedCount = failedGroups.reduce(
      (sum, group) => sum + (group.count || 0),
      0
    )
    const validSources = Array.from(sourceMap.values())

    return {
      ...previous,
      deepInvalid: failedCount,
      validCount: validSources.length,
      dedupedSources: validSources,
      failedGroups,
      failedCategories: data.failedCategories || previous.failedCategories || {},
      ruleTypeStats: data.ruleTypeStats || previous.ruleTypeStats || null
    }
  }

  return {
    isNetworkRetryReason,
    isRetryableGroup,
    normalizeFailedSource,
    collectFailedSources,
    mergeRetryResultData
  }
}
