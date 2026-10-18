// 单个处理流程组合式函数
// 负责单文件/在线链接的去重与深度校验编排。
import { computed, ref } from 'vue'
import {
  getProgressEventSource,
  parseFile,
  parseUrl,
  startValidation,
  startValidationFromData
} from '../api/sources.js'
import {
  buildValidationResultData,
  fetchValidationResult
} from '../utils/validationResult.js'

/**
 * @param {Object} deps 由 App.vue 注入的共享状态与方法
 */
export function useSingleProcess(deps) {
  const {
    state,
    setFile,
    setLoading,
    setValidating,
    setError,
    setSourceData,
    setSuccess,
    showError,
    showSuccess,
    showWarning,
    concurrency,
    timeout,
    filterTypes,
    validationMode,
    sessionId,
    startResultData,
    progressData,
    elapsedTime,
    subscribeValidation,
    stopValidation,
    isSingleMode
  } = deps

  // 在线解析：输入链接与解析后的原始数据（用于后续深度校验）
  const urlInput = ref('')
  const urlSourceData = ref(null)
  const hasUrlData = computed(() => !!urlSourceData.value)

  function handleFileUpload(file) {
    setFile(file)
    urlSourceData.value = null
  }

  async function handleUrlFetch(url) {
    setLoading(true)
    setError(null)
    urlInput.value = url

    const filterTypesStr = filterTypes.value.join(',')

    try {
      const result = await parseUrl(
        url, 'dedup', concurrency.value, timeout.value,
        filterTypesStr, validationMode.value
      )

      if (result.code !== 200) {
        showError(result.message)
        return
      }

      urlSourceData.value = result.data
      setSourceData(result.data)
      showSuccess(`在线解析成功，共 ${result.data.total} 条书源`)
    } catch (err) {
      showError('网络错误，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  async function handleDedupFile() {
    if (!state.file) return

    setLoading(true)
    setError(null)

    const filterTypesStr = filterTypes.value.join(',')

    try {
      const result = await parseFile(
        state.file, 'dedup', concurrency.value, timeout.value,
        filterTypesStr, validationMode.value
      )

      if (result.code !== 200) {
        showError(result.message)
        return
      }

      setSourceData(result.data)
      const duplicatesRemoved = result.data.total - result.data.validCount
      if (duplicatesRemoved > 0) {
        showSuccess(`去重完成，移除 ${duplicatesRemoved} 条重复，有效 ${result.data.validCount} 条`)
      } else {
        showSuccess(`去重完成，有效书源 ${result.data.validCount} 条`)
      }
    } catch (err) {
      showError('处理失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  async function handleDedupOnly() {
    if (state.file) {
      await handleDedupFile()
    } else if (urlSourceData.value) {
      setSourceData(urlSourceData.value)
      showSuccess(`去重完成，有效书源 ${urlSourceData.value.validCount} 条`)
    }
  }

  async function handleFullValidateFile() {
    if (!state.file) return

    setValidating(true)
    setError(null)
    progressData.value = null
    startResultData.value = null

    const filterTypesStr = filterTypes.value.join(',')

    try {
      const startResult = await startValidation(
        state.file, concurrency.value, timeout.value,
        filterTypesStr, validationMode.value
      )

      if (startResult.code !== 200) {
        showError(startResult.message)
        setValidating(false)
        return
      }

      startResultData.value = startResult
      sessionId.value = startResult.sessionId

      subscribeValidation({
        label: '校验',
        createSource: () => getProgressEventSource(sessionId.value),
        initialProgress: { total: startResult.deepTotal },
        onCompleted: async () => {
          try {
            const result = await fetchValidationResult(sessionId.value)
            const startData = startResultData.value
            setSourceData(buildValidationResultData(startData, result))
            const invalidTotal = (startData.formatInvalid || 0) + (result.invalidCount || 0)
            if (invalidTotal > 0) {
              showSuccess(`校验完成，有效 ${result.validCount} 条，失效 ${invalidTotal} 条`)
            } else {
              showSuccess(`校验完成，全部有效，共 ${result.validCount} 条`)
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
            setSourceData(buildValidationResultData(startResultData.value, result))
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
      showError('校验失败，请稍后重试')
      setValidating(false)
    }
  }

  async function handleFullValidateUrl() {
    if (!urlSourceData.value) return

    setValidating(true)
    setError(null)

    try {
      const result = await startValidationFromData(
        urlSourceData.value.dedupedSources || [],
        concurrency.value,
        timeout.value,
        validationMode.value
      )

      if (result.code !== 200) {
        showError(result.message)
        setValidating(false)
        return
      }

      sessionId.value = result.sessionId

      subscribeValidation({
        label: '校验',
        createSource: () => getProgressEventSource(sessionId.value),
        initialProgress: { total: urlSourceData.value.dedupedSources?.length || 0 },
        onCompleted: async () => {
          try {
            const result = await fetchValidationResult(sessionId.value)
            setSourceData(buildValidationResultData(urlSourceData.value, result))
            const invalidTotal = (urlSourceData.value.formatInvalid || 0) + (result.invalidCount || 0)
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
            setSourceData(buildValidationResultData(urlSourceData.value, result))
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
      showError('校验失败，请稍后重试')
      setValidating(false)
    }
  }

  async function handleFullValidate() {
    if (state.file) {
      await handleFullValidateFile()
    } else if (urlSourceData.value) {
      await handleFullValidateUrl()
    }
  }

  // 全局粘贴事件处理（仅在单个处理模式生效）
  function handleGlobalPaste(e) {
    if (state.loading || state.validating) return
    if (!isSingleMode()) return

    const text = e.clipboardData.getData('text')
    if (text && text.trim().startsWith('http')) {
      e.preventDefault()
      handleUrlFetch(text.trim())
    }
  }

  async function pasteAndParse() {
    try {
      const text = await navigator.clipboard.readText()
      if (text && text.trim().startsWith('http')) {
        handleUrlFetch(text.trim())
      } else {
        showWarning('剪贴板内容不是有效的链接')
      }
    } catch (err) {
      showError('无法读取剪贴板')
    }
  }

  function reset() {
    urlInput.value = ''
    urlSourceData.value = null
  }

  return {
    urlInput,
    urlSourceData,
    hasUrlData,
    handleFileUpload,
    handleUrlFetch,
    handleDedupOnly,
    handleFullValidate,
    handleGlobalPaste,
    pasteAndParse,
    reset
  }
}
