// 书源数据处理组合式函数
import { reactive, computed } from 'vue'

/**
 * 使用书源状态管理
 */
export function useSources() {
  const state = reactive({
    // 文件状态
    file: null,
    fileName: null,

    // 加载状态
    loading: false,
    validating: false,

    // 消息状态
    error: null,
    success: null,
    warning: null,

    // 数据状态
    sourceData: null
  })

  // 计算属性
  const hasFile = computed(() => !!state.file)

  const hasValidSources = computed(() =>
    state.sourceData && state.sourceData.validCount > 0
  )

  const stats = computed(() => {
    if (!state.sourceData) return null
    return {
      total: state.sourceData.total,
      dedupCount: state.sourceData.dedupCount,
      duplicates: state.sourceData.duplicates || 0,
      duplicateUrls: state.sourceData.duplicateUrls || [],
      formatInvalid: state.sourceData.formatInvalid,
      deepInvalid: state.sourceData.deepInvalid,
      validCount: state.sourceData.validCount,
      // 规则类型统计（搜索校验模式）
      ruleTypeStats: state.sourceData.ruleTypeStats || null
    }
  })

  // 方法
  function setFile(file) {
    state.file = file
    state.fileName = file.name
    // 重置数据
    state.sourceData = null
    state.error = null
    state.success = null
    state.warning = null
  }

  function setLoading(value) {
    state.loading = value
  }

  function setValidating(value) {
    state.validating = value
  }

  function setError(message) {
    state.error = message
    state.success = null
    state.warning = null
  }

  function setSuccess(message) {
    state.success = message
    state.error = null
    state.warning = null
  }

  function setWarning(message) {
    state.warning = message
    state.error = null
    state.success = null
  }

  function setSourceData(data) {
    state.sourceData = data
  }

  function reset() {
    state.file = null
    state.fileName = null
    state.loading = false
    state.validating = false
    state.error = null
    state.success = null
    state.warning = null
    state.sourceData = null
  }

  function clearMessages() {
    state.error = null
    state.success = null
    state.warning = null
  }

  return {
    state,
    hasFile,
    hasValidSources,
    stats,
    setFile,
    setLoading,
    setValidating,
    setError,
    setSuccess,
    setWarning,
    setSourceData,
    reset,
    clearMessages
  }
}