// 导出到阅读 App 组合式函数
// 负责临时导出链接的生成、缓存与过期提示。
import { computed, ref } from 'vue'
import { createBookSourceExport } from '../api/sources.js'
import {
  buildAbsoluteUrl,
  buildLegadoImportUrl,
  formatDate
} from '../utils/download.js'

function createEmptyLegadoExport() {
  return {
    ready: false,
    loading: false,
    downloadUrl: '',
    legadoUrl: '',
    expiresAt: 0,
    sourceCount: 0
  }
}

/**
 * @param {Object} options
 * @param {() => Array} options.getSources 获取当前有效书源数组
 * @param {() => number} options.getValidCount 获取当前有效书源数量
 * @param {(message: string) => void} options.showError
 * @param {(message: string) => void} options.showWarning
 */
export function useLegadoExport({
  getSources,
  getValidCount,
  showError = () => {},
  showWarning = () => {}
}) {
  const legadoExport = ref(createEmptyLegadoExport())

  const exportSourceFilename = computed(
    () => `阅读书源_去重有效_${formatDate(new Date())}.json`
  )

  const legadoExportExpireText = computed(() => {
    if (!legadoExport.value.expiresAt) return ''

    const remainingSeconds = Math.max(
      0,
      legadoExport.value.expiresAt - Math.floor(Date.now() / 1000)
    )
    if (remainingSeconds <= 0) return '临时链接已过期'
    if (remainingSeconds > 60) return `约 ${Math.ceil(remainingSeconds / 60)} 分钟后失效`
    return `约 ${remainingSeconds} 秒后失效`
  })

  function reset() {
    legadoExport.value = createEmptyLegadoExport()
  }

  function getCached() {
    const current = legadoExport.value
    const currentValidCount = getValidCount()
    const isFresh = (
      current.ready &&
      current.downloadUrl &&
      current.legadoUrl &&
      current.sourceCount === currentValidCount &&
      current.expiresAt > Math.floor(Date.now() / 1000) + 30
    )

    return isFresh ? current : null
  }

  async function ensureReady({ silent = false } = {}) {
    const sources = getSources()
    if (!Array.isArray(sources) || sources.length === 0) {
      if (!silent) {
        showWarning('没有可导出的有效书源')
      }
      return null
    }

    const cached = getCached()
    if (cached) {
      return cached
    }

    legadoExport.value = {
      ...createEmptyLegadoExport(),
      loading: true,
      sourceCount: sources.length
    }

    try {
      const result = await createBookSourceExport(sources, exportSourceFilename.value)
      if (result.code !== 200) {
        throw new Error(result.message || '生成导出链接失败')
      }

      const downloadUrl = buildAbsoluteUrl(result.data.path)
      legadoExport.value = {
        ready: true,
        loading: false,
        downloadUrl,
        legadoUrl: buildLegadoImportUrl(downloadUrl),
        expiresAt: result.data.expiresAt,
        sourceCount: sources.length
      }
      return legadoExport.value
    } catch (err) {
      reset()
      if (!silent) {
        showError(err.message || '生成导出链接失败')
      }
      return null
    }
  }

  return {
    legadoExport,
    exportSourceFilename,
    legadoExportExpireText,
    reset,
    getCached,
    ensureReady
  }
}
