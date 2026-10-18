// 批量处理流程组合式函数
// 负责批量去重（普通请求）与批量校验（SSE）的编排。
import {
  getProgressEventSource,
  parseBatchFiles,
  parseBatchUrls,
  startBatchFilesValidation,
  startBatchUrlsValidation
} from '../api/sources.js'
import {
  buildValidationResultData,
  fetchValidationResult
} from '../utils/validationResult.js'

/**
 * @param {Object} deps 由 App.vue 注入的共享状态与方法
 */
export function useBatchProcess(deps) {
  const {
    state,
    setLoading,
    setValidating,
    setError,
    setSourceData,
    setSuccess,
    showError,
    showWarning,
    progressData,
    elapsedTime,
    subscribeValidation,
    stopValidation,
    concurrency,
    timeout,
    filterTypes,
    validationMode,
    sessionId,
    startResultData,
    batchProcessorRef
  } = deps

  function applyBatchStats(stats) {
    if (batchProcessorRef.value) {
      batchProcessorRef.value.setStats(stats)
    }
  }

  async function handleBatchDedup({ type, data }) {
    setLoading(true)
    try {
      const filterTypesStr = filterTypes.value.join(',')
      const result = type === 'files'
        ? await parseBatchFiles(
            data, 'dedup', concurrency.value, timeout.value,
            filterTypesStr, validationMode.value
          )
        : await parseBatchUrls(
            data, 'dedup', concurrency.value, timeout.value,
            filterTypesStr, validationMode.value
          )

      if (result.code !== 200) {
        showError(result.message)
        return
      }

      applyBatchStats({
        fileStats: result.data.fileStats,
        urlStats: result.data.urlStats
      })

      setSourceData(result.data)
      setSuccess(`批量去重完成！有效书源 ${result.data.validCount} 条`)
    } catch (err) {
      showError('批量处理失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  function startBatchValidation({ type, data }) {
    const filterTypesStr = filterTypes.value.join(',')
    return type === 'files'
      ? startBatchFilesValidation(
          data, concurrency.value, timeout.value,
          filterTypesStr, validationMode.value
        )
      : startBatchUrlsValidation(
          data, concurrency.value, timeout.value,
          filterTypesStr, validationMode.value
        )
  }

  function buildBatchResult(base, result) {
    return buildValidationResultData({
      total: result.totalOriginal || base.total,
      dedupCount: result.dedupCount || base.deepTotal,
      duplicates: result.duplicates || 0,
      formatInvalid: result.formatInvalid || 0
    }, result)
  }

  async function handleBatchValidate({ type, data }) {
    setValidating(true)
    progressData.value = null
    startResultData.value = null

    try {
      const startResult = await startBatchValidation({ type, data })

      if (startResult.code !== 200) {
        showError(startResult.message)
        setValidating(false)
        return
      }

      startResultData.value = startResult
      sessionId.value = startResult.sessionId

      applyBatchStats({
        fileStats: startResult.fileStats,
        urlStats: startResult.urlStats
      })

      subscribeValidation({
        label: '批量校验',
        createSource: () => getProgressEventSource(sessionId.value),
        initialProgress: { total: startResult.deepTotal },
        onCompleted: async () => {
          try {
            const result = await fetchValidationResult(sessionId.value)
            setSourceData(buildBatchResult(startResult, result))
            const invalidTotal = (result.formatInvalid || 0) + (result.invalidCount || 0)
            if (invalidTotal > 0) {
              setSuccess(`校验完成！有效书源 ${result.validCount} 条，失效 ${invalidTotal} 条，耗时 ${elapsedTime.value} 秒`)
            } else {
              setSuccess(`校验完成！有效书源 ${result.validCount} 条，耗时 ${elapsedTime.value} 秒`)
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
            setSourceData(buildBatchResult(startResult, result))
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
      showError('批量校验失败，请稍后重试')
      setValidating(false)
    }
  }

  async function handleBatchProcess({ type, data, mode }) {
    setError(null)

    if (mode === 'dedup') {
      await handleBatchDedup({ type, data })
      return
    }

    await handleBatchValidate({ type, data })
  }

  return { handleBatchProcess }
}
