// 搜索校验流程组合式函数
// 负责搜索/发现规则校验的启动、SSE 订阅与结果组装。
import { ref } from 'vue'
import {
  getSearchProgressEventSource,
  startSearchValidation
} from '../api/sources.js'
import {
  buildValidationResultData,
  fetchValidationResult
} from '../utils/validationResult.js'

/**
 * @param {Object} deps 由 App.vue 注入的共享状态与方法
 */
export function useSearchValidation(deps) {
  const {
    state,
    setValidating,
    setError,
    setSourceData,
    setSuccess,
    showError,
    showWarning,
    validationMode,
    sessionId,
    progressData,
    elapsedTime,
    subscribeValidation,
    stopValidation
  } = deps

  // 最近一次搜索校验配置，用于失败重试
  const lastSearchConfig = ref({
    validateType: 'search',
    keyword: '玄幻'
  })

  async function handleSearchValidation(payload) {
    const {
      validateType,
      keyword,
      concurrency: searchConcurrency,
      timeout: searchTimeout,
      validationMode: searchValidationMode
    } = payload

    if (!state.file) {
      showError('请先上传书源文件')
      return
    }

    lastSearchConfig.value = { validateType, keyword }

    setValidating(true)
    setError(null)

    try {
      const startResult = await startSearchValidation(
        state.file,
        keyword,
        validateType,
        searchConcurrency || 16,
        searchTimeout || 30,
        searchValidationMode || validationMode.value
      )

      if (startResult.code !== 200) {
        showError(startResult.message)
        setValidating(false)
        return
      }

      sessionId.value = startResult.sessionId

      const typeLabel = validateType === 'search' ? '搜索' : '发现'
      const buildBase = () => ({
        total: startResult.total,
        dedupCount: startResult.total,
        duplicates: 0,
        formatInvalid: 0
      })

      subscribeValidation({
        label: '搜索校验',
        createSource: () => getSearchProgressEventSource(sessionId.value),
        initialProgress: { total: startResult.total },
        onCompleted: async () => {
          try {
            const result = await fetchValidationResult(sessionId.value)
            setSourceData(buildValidationResultData(buildBase(), result, {
              ruleTypeStats: result.ruleTypeStats || null
            }))
            if (result.invalidCount > 0) {
              setSuccess(`${typeLabel}校验完成！有效书源 ${result.validCount} 条，失效 ${result.invalidCount} 条，耗时 ${elapsedTime.value} 秒`)
            } else {
              setSuccess(`${typeLabel}校验完成！有效书源 ${result.validCount} 条，耗时 ${elapsedTime.value} 秒`)
            }
          } catch (err) {
            showError('获取校验结果失败，请重试或刷新页面')
          } finally {
            setValidating(false)
          }
        },
        onCancelled: async () => {
          try {
            const result = await fetchValidationResult(sessionId.value)
            setSourceData(buildValidationResultData(buildBase(), result, {
              ruleTypeStats: result.ruleTypeStats || null
            }))
            showWarning(`校验已取消，已保留 ${result.validCount} 条有效结果`)
          } catch (err) {
            progressData.value = null
            showWarning('校验已取消')
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
      showError('搜索校验失败，请稍后重试')
      setValidating(false)
    }
  }

  return { lastSearchConfig, handleSearchValidation }
}
