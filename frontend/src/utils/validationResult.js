// 校验结果组装与拉取工具
import { getValidationResult } from '../api/sources.js'

/**
 * 组装校验结果数据（结果接口数据 + 会话基础统计）
 * @param {Object} base 会话基础统计（total/dedupCount/duplicates/formatInvalid）
 * @param {Object} data 结果接口返回的数据
 * @param {Object} extras 额外字段（如 ruleTypeStats）
 */
export function buildValidationResultData(base, data, extras = {}) {
  return {
    total: base.total,
    dedupCount: base.dedupCount,
    duplicates: base.duplicates,
    duplicateUrls: [],
    formatInvalid: base.formatInvalid,
    deepInvalid: data.invalidCount,
    validCount: data.validCount,
    dedupedSources: data.validSources || [],
    failedGroups: data.failedGroups || [],
    failedCategories: data.failedCategories || {},
    ...extras
  }
}

/**
 * 拉取完整校验结果（弱网下与 SSE 分离，失败自动重试一次）
 * @param {string} sessionIdValue 会话 ID
 */
export async function fetchValidationResult(sessionIdValue) {
  let lastError = null
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const result = await getValidationResult(sessionIdValue)
      if (result.code !== 200) {
        throw new Error(result.message || '获取校验结果失败')
      }
      return result.data
    } catch (err) {
      lastError = err
      if (attempt === 0) {
        await new Promise((resolve) => setTimeout(resolve, 800))
      }
    }
  }
  throw lastError || new Error('获取校验结果失败')
}
