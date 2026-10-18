// 失败书源重试组合式函数
// 纯逻辑：失败分组筛选、书源归一化、重试结果合并；
// 编排：失败重试会话的启动与 SSE 订阅。
import {
  getProgressEventSource,
  getSearchProgressEventSource,
  startSearchValidationFromData,
  startValidationFromData
} from '../api/sources.js'
import { fetchValidationResult } from '../utils/validationResult.js'

// 旧数据兜底：失败原因中文关键词匹配
const NETWORK_RETRY_KEYWORDS = [
  '超时', '连接失败', '连接超时', '读取错误', '写入错误',
  '读取超时', '写入超时', '网络错误', 'SSL', '服务器断开', '协议错误'
]

/**
 * @param {Object} deps 编排依赖（纯逻辑函数在无依赖时也可单独使用）
 */
export function useFailedRetry(deps = {}) {
  const {
    state,
    setValidating = () => {},
    setSourceData = () => {},
    progressData = { value: null },
    subscribeValidation = () => {},
    stopValidation = () => {},
    concurrency = { value: 16 },
    timeout = { value: 30 },
    validationMode = { value: 'custom' },
    sessionId = { value: null },
    processMode = { value: 'single' },
    lastSearchConfig = { value: { validateType: 'search', keyword: '玄幻' } },
    showSuccess = () => {},
    showWarning = () => {},
    showError = () => {}
  } = deps

  // 当前重试上下文（无需响应式，仅流程内部使用）
  let retryContext = null

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

  function mergeRetryResult(data, skippedGroups = []) {
    if (!retryContext?.previous) return
    const merged = mergeRetryResultData(
      retryContext.previous,
      data,
      skippedGroups
    )
    if (merged) setSourceData(merged)
  }

  async function startRetrySession(retrySources, isSearch) {
    if (isSearch) {
      return startSearchValidationFromData(
        retrySources,
        lastSearchConfig.value.keyword,
        lastSearchConfig.value.validateType,
        concurrency.value,
        timeout.value,
        validationMode.value
      )
    }
    return startValidationFromData(
      retrySources,
      concurrency.value,
      timeout.value,
      validationMode.value
    )
  }

  async function handleRetryFailed(onlyNetwork) {
    const sourceData = state?.sourceData
    const { retrySources, skippedGroups } = collectFailedSources(
      sourceData,
      onlyNetwork
    )
    if (retrySources.length === 0) {
      showWarning(onlyNetwork ? '没有可重试的网络/超时失败项' : '没有可重试的失败项')
      return
    }

    const isSearch = processMode.value === 'search'
    retryContext = {
      previous: sourceData,
      skippedGroups,
      onlyNetwork,
      isSearch
    }

    setValidating(true)
    progressData.value = {
      processed: 0,
      total: retrySources.length,
      valid: 0,
      invalid: 0,
      current: '',
      currentName: '',
      estimatedRemaining: 0,
      status: 'running'
    }

    try {
      const startResult = await startRetrySession(retrySources, isSearch)

      if (startResult.code !== 200) {
        showError(startResult.message)
        setValidating(false)
        return
      }

      sessionId.value = startResult.sessionId

      subscribeValidation({
        label: '失败重试',
        createSource: () => isSearch
          ? getSearchProgressEventSource(sessionId.value)
          : getProgressEventSource(sessionId.value),
        initialProgress: { total: retrySources.length },
        onCompleted: async () => {
          try {
            const result = await fetchValidationResult(sessionId.value)
            mergeRetryResult(result, skippedGroups)
            retryContext = null
            showSuccess(`重试完成，新增/保留有效 ${result.validCount} 条，仍失败 ${result.invalidCount || 0} 条`)
          } catch (err) {
            showError('获取重试结果失败，请稍后重试')
          } finally {
            setValidating(false)
          }
        },
        onCancelled: async () => {
          try {
            const result = await fetchValidationResult(sessionId.value)
            mergeRetryResult(result, skippedGroups)
            retryContext = null
            showSuccess(`重试已取消，新增/保留有效 ${result.validCount} 条，仍失败 ${result.invalidCount || 0} 条`)
          } catch (err) {
            progressData.value = null
            showWarning('重试已取消')
          } finally {
            setValidating(false)
          }
        },
        onError: (message) => {
          setValidating(false)
          showError(message)
        }
      })

    } catch (err) {
      stopValidation()
      setValidating(false)
      showError('重试失败，请稍后再试')
    }
  }

  return {
    isNetworkRetryReason,
    isRetryableGroup,
    normalizeFailedSource,
    collectFailedSources,
    mergeRetryResultData,
    handleRetryFailed
  }
}
