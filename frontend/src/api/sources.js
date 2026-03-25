// API接口封装
import axios from 'axios'

const API_BASE = '/api'

/**
 * 健康检查
 */
export async function healthCheck() {
  const response = await axios.get(`${API_BASE}/health`)
  return response.data
}

/**
 * 解析上传的文件
 * @param {File} file - JSON文件
 * @param {string} mode - 操作模式: 'dedup'(只查重复) 或 'full'(全部校验)
 * @param {number} concurrency - 深度校验并发数 (1/4/8/16/32)
 * @param {number} timeout - 深度校验超时时间 (15/30/45/60秒)
 * @param {string} filterTypes - 过滤类型（逗号分隔）
 */
export async function parseFile(file, mode = 'dedup', concurrency = 16, timeout = 30, filterTypes = '') {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('mode', mode)
  formData.append('concurrency', concurrency)
  formData.append('timeout', timeout)
  formData.append('filter_types', filterTypes)

  const response = await axios.post(`${API_BASE}/parse/file`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

/**
 * 解析在线链接
 * @param {string} url - 书源JSON文件的URL
 * @param {string} mode - 操作模式: 'dedup' 或 'full'
 * @param {number} concurrency - 深度校验并发数 (1/4/8/16/32)
 * @param {number} timeout - 深度校验超时时间 (15/30/45/60秒)
 * @param {string} filterTypes - 过滤类型（逗号分隔）
 */
export async function parseUrl(url, mode = 'dedup', concurrency = 16, timeout = 30, filterTypes = '') {
  const response = await axios.post(`${API_BASE}/parse/url`, { url, mode, concurrency, timeout, filter_types: filterTypes })
  return response.data
}

/**
 * 创建临时书源导出链接
 * @param {Array} sources - 有效书源数组
 * @param {string} filename - 导出文件名
 */
export async function createBookSourceExport(sources, filename) {
  const response = await axios.post(`${API_BASE}/export/book-source`, {
    sources,
    filename
  })
  return response.data
}

/**
 * 开始深度校验（SSE模式）- 文件上传
 * @param {File} file - JSON文件
 * @param {number} concurrency - 并发数
 * @param {number} timeout - 超时时间
 * @param {string} filterTypes - 过滤类型（逗号分隔）
 * @returns {Promise<{code: number, sessionId: string, total: number}>}
 */
export async function startValidation(file, concurrency = 16, timeout = 30, filterTypes = '') {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('concurrency', concurrency)
  formData.append('timeout', timeout)
  formData.append('filter_types', filterTypes)

  const response = await axios.post(`${API_BASE}/validate/start`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

/**
 * 开始深度校验（SSE模式）- 从已解析数据
 * @param {Array} sources - 已解析的书源数组
 * @param {number} concurrency - 并发数
 * @param {number} timeout - 超时时间
 * @returns {Promise<{code: number, sessionId: string}>}
 */
export async function startValidationFromData(sources, concurrency = 16, timeout = 30) {
  const response = await axios.post(`${API_BASE}/validate/start-data`, {
    sources,
    concurrency,
    timeout
  })
  return response.data
}

/**
 * 获取 SSE 进度连接
 * @param {string} sessionId - 会话ID
 * @returns {EventSource}
 */
export function getProgressEventSource(sessionId) {
  return new EventSource(`${API_BASE}/validate/progress/${sessionId}`)
}

/**
 * 获取搜索校验 SSE 进度连接
 * @param {string} sessionId - 会话ID
 * @returns {EventSource}
 */
export function getSearchProgressEventSource(sessionId) {
  return new EventSource(`${API_BASE}/validate/search/progress/${sessionId}`)
}

/**
 * 取消校验
 * @param {string} sessionId - 会话ID
 */
export async function cancelValidation(sessionId) {
  const formData = new FormData()
  formData.append('session_id', sessionId)
  const response = await axios.post(`${API_BASE}/validate/cancel`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

/**
 * 批量解析多个文件
 * @param {File[]} files - JSON文件数组
 * @param {string} mode - 操作模式: 'dedup' 或 'full'
 * @param {number} concurrency - 深度校验并发数
 * @param {number} timeout - 深度校验超时时间
 * @param {string} filterTypes - 过滤类型（逗号分隔）
 */
export async function parseBatchFiles(files, mode = 'dedup', concurrency = 16, timeout = 30, filterTypes = '') {
  const formData = new FormData()
  files.forEach(file => {
    formData.append('files', file)
  })
  formData.append('mode', mode)
  formData.append('concurrency', concurrency)
  formData.append('timeout', timeout)
  formData.append('filter_types', filterTypes)

  const response = await axios.post(`${API_BASE}/parse/batch-files`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

/**
 * 批量解析多个URL
 * @param {string[]} urls - URL数组
 * @param {string} mode - 操作模式: 'dedup' 或 'full'
 * @param {number} concurrency - 深度校验并发数
 * @param {number} timeout - 深度校验超时时间
 * @param {string} filterTypes - 过滤类型（逗号分隔）
 */
export async function parseBatchUrls(urls, mode = 'dedup', concurrency = 16, timeout = 30, filterTypes = '') {
  const response = await axios.post(`${API_BASE}/parse/batch-urls`, {
    urls,
    mode,
    concurrency,
    timeout,
    filter_types: filterTypes
  })
  return response.data
}

/**
 * 开始批量文件校验（SSE模式）
 * @param {File[]} files - JSON文件数组
 * @param {number} concurrency - 并发数
 * @param {number} timeout - 超时时间
 * @param {string} filterTypes - 过滤类型（逗号分隔）
 * @returns {Promise<{code: number, sessionId: string, fileStats: Array}>}
 */
export async function startBatchFilesValidation(files, concurrency = 16, timeout = 30, filterTypes = '') {
  const formData = new FormData()
  files.forEach(file => {
    formData.append('files', file)
  })
  formData.append('concurrency', concurrency)
  formData.append('timeout', timeout)
  formData.append('filter_types', filterTypes)

  const response = await axios.post(`${API_BASE}/parse/batch-files/start`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

/**
 * 开始批量URL校验（SSE模式）
 * @param {string[]} urls - URL数组
 * @param {number} concurrency - 并发数
 * @param {number} timeout - 超时时间
 * @param {string} filterTypes - 过滤类型（逗号分隔）
 * @returns {Promise<{code: number, sessionId: string, urlStats: Array}>}
 */
export async function startBatchUrlsValidation(urls, concurrency = 16, timeout = 30, filterTypes = '') {
  const response = await axios.post(`${API_BASE}/parse/batch-urls/start`, {
    urls,
    concurrency,
    timeout,
    filter_types: filterTypes
  })
  return response.data
}

/**
 * 开始搜索校验（SSE模式）
 * @param {File} file - JSON文件
 * @param {string} keyword - 搜索关键词
 * @param {string} validateType - 校验类型 'search' 或 'explore'
 * @param {number} concurrency - 并发数
 * @param {number} timeout - 超时时间
 * @returns {Promise<{code: number, sessionId: string, total: number}>}
 */
export async function startSearchValidation(file, keyword = '玄幻', validateType = 'search', concurrency = 16, timeout = 30) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('keyword', keyword)
  formData.append('validate_type', validateType)
  formData.append('concurrency', concurrency)
  formData.append('timeout', timeout)

  const response = await axios.post(`${API_BASE}/validate/search/start`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}
