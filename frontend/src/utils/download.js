// 文件下载工具

/**
 * 下载JSON文件
 * @param {any} data - JSON数据
 * @param {string} filename - 文件名
 */
export function downloadJson(data, filename) {
  const json = JSON.stringify(data, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  URL.revokeObjectURL(url)
}

/**
 * 构造当前站点下的绝对地址
 * @param {string} path - 相对路径
 * @returns {string}
 */
export function buildAbsoluteUrl(path) {
  return new URL(path, window.location.origin).toString()
}

/**
 * 构造阅读 App 导入链接
 * @param {string} downloadUrl - 可访问的 JSON 下载地址
 * @returns {string}
 */
export function buildLegadoImportUrl(downloadUrl) {
  return `legado://import/bookSource?src=${encodeURIComponent(downloadUrl)}`
}

/**
 * 打开外部链接或自定义 Scheme
 * @param {string} url - 外部地址
 */
export function openExternalUrl(url) {
  const link = document.createElement('a')
  link.href = url
  link.rel = 'noreferrer'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

/**
 * 格式化日期
 * @param {Date} date - 日期对象
 * @returns {string} 格式化后的日期字符串 YYYY-MM-DD
 */
export function formatDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
