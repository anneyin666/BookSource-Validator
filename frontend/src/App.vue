<template>
  <div class="app-container">
    <!-- 主题切换按钮 -->
    <ThemeToggle />

    <!-- 头部 -->
    <header class="app-header">
      <h1 class="title">📚 阅读书源 · 净源工坊</h1>
      <p class="subtitle">⚡ 上传/在线解析 · 自动去重深度校验</p>
    </header>

    <!-- 消息提示 -->
    <MessageAlert
      v-if="state.error || state.success || state.warning"
      :error="state.error"
      :success="state.success"
      :warning="state.warning"
      @close="clearMessages"
    />

    <!-- 操作区域 -->
    <main class="main-content">
      <!-- 模式切换 -->
      <div class="mode-switch">
        <button
          :class="['mode-btn', { active: processMode === 'single' }]"
          @click="processMode = 'single'"
        >
          📄 单个处理
        </button>
        <button
          :class="['mode-btn', { active: processMode === 'batch' }]"
          @click="processMode = 'batch'"
        >
          📦 批量处理
        </button>
        <button
          :class="['mode-btn', { active: processMode === 'search' }]"
          @click="processMode = 'search'"
        >
          🔍 搜索校验
        </button>
      </div>

      <!-- 单个处理模式 -->
      <template v-if="processMode === 'single'">
        <div class="input-section">
          <FileUpload
            :loading="state.loading || state.validating"
            :file-name="state.fileName"
            @upload="handleFileUpload"
          />

          <UrlInput
            :loading="state.loading || state.validating"
            :url="urlInput"
            @fetch="handleUrlFetch"
            @paste="pasteAndParse"
          />
        </div>

        <!-- 清除按钮 -->
        <button
          v-if="hasFile || hasUrlData"
          class="clear-btn"
          @click="handleClear"
          :disabled="state.loading || state.validating"
        >
          🗑️ 清除
        </button>

        <!-- 操作按钮 -->
        <ActionButtons
          v-if="hasFile || hasUrlData"
          :loading="state.loading"
          :validating="state.validating"
          @dedup="handleDedupOnly"
          @full-validate="handleFullValidate"
        />

        <!-- 设置区域 -->
        <div v-if="(hasFile || hasUrlData) && !state.loading && !state.validating && !state.sourceData" class="settings-section">
          <ConcurrencySelector v-model="concurrency" />
          <TimeoutSelector v-model="timeout" />
          <FilterOptions v-model="filterTypes" />
        </div>
      </template>

      <!-- 批量处理模式 -->
      <template v-if="processMode === 'batch'">
        <BatchProcessor
          ref="batchProcessorRef"
          :loading="state.loading || state.validating"
          :concurrency="concurrency"
          :timeout="timeout"
          :filter-types="filterTypes"
          @batch-process="handleBatchProcess"
        />

        <!-- 设置区域（批量模式也显示） -->
        <div v-if="!state.loading && !state.validating && !state.sourceData" class="settings-section">
          <ConcurrencySelector v-model="concurrency" />
          <TimeoutSelector v-model="timeout" />
          <FilterOptions v-model="filterTypes" />
        </div>
      </template>

      <!-- 搜索校验模式 -->
      <template v-if="processMode === 'search'">
        <FileUpload
          :loading="state.validating"
          :file-name="state.fileName"
          @upload="handleFileUpload"
        />

        <SearchValidator
          v-if="hasFile && !state.sourceData"
          :loading="state.validating"
          @start-validation="handleSearchValidation"
        />

        <!-- 清除按钮 -->
        <button
          v-if="state.sourceData"
          class="reset-btn"
          @click="handleClear"
        >
          🗑️ 清除重新校验
        </button>
      </template>

      <!-- SSE 实时进度条 -->
      <ValidationProgress
        v-if="state.validating && progressData"
        :processed="progressData.processed"
        :total="progressData.total"
        :valid="progressData.valid"
        :invalid="progressData.invalid"
        :current-url="progressData.current"
        :current-name="progressData.currentName"
        :elapsed-time="elapsedTime"
        :estimated-remaining="progressData.estimatedRemaining || 0"
        @cancel="handleCancelValidation"
      />

      <!-- 统计结果 -->
      <section class="stats-section" v-if="state.sourceData">
        <h2 class="section-title">📊 统计结果</h2>
        <StatsCardGroup :stats="stats" />

        <!-- 规则类型统计（搜索校验模式） -->
        <div v-if="stats.ruleTypeStats && processMode === 'search'" class="rule-type-stats">
          <h3 class="rule-type-title">📋 规则类型分布</h3>
          <div class="rule-type-cards">
            <div class="rule-type-card search-only">
              <div class="rule-type-label">🔍 仅搜索</div>
              <div class="rule-type-numbers">
                <span class="valid">{{ stats.ruleTypeStats.searchOnly.valid }} 有效</span>
                <span class="invalid">{{ stats.ruleTypeStats.searchOnly.invalid }} 失效</span>
              </div>
              <div class="rule-type-total">共 {{ stats.ruleTypeStats.searchOnly.total }} 条</div>
            </div>
            <div class="rule-type-card explore-only">
              <div class="rule-type-label">📖 仅发现</div>
              <div class="rule-type-numbers">
                <span class="valid">{{ stats.ruleTypeStats.exploreOnly.valid }} 有效</span>
                <span class="invalid">{{ stats.ruleTypeStats.exploreOnly.invalid }} 失效</span>
              </div>
              <div class="rule-type-total">共 {{ stats.ruleTypeStats.exploreOnly.total }} 条</div>
            </div>
            <div class="rule-type-card both">
              <div class="rule-type-label">🔍📖 搜索+发现</div>
              <div class="rule-type-numbers">
                <span class="valid">{{ stats.ruleTypeStats.both.valid }} 有效</span>
                <span class="invalid">{{ stats.ruleTypeStats.both.invalid }} 失效</span>
              </div>
              <div class="rule-type-total">共 {{ stats.ruleTypeStats.both.total }} 条</div>
            </div>
            <div class="rule-type-card none" v-if="stats.ruleTypeStats.none.total > 0">
              <div class="rule-type-label">❌ 无规则</div>
              <div class="rule-type-numbers">
                <span class="invalid">{{ stats.ruleTypeStats.none.invalid }} 失效</span>
              </div>
              <div class="rule-type-total">共 {{ stats.ruleTypeStats.none.total }} 条</div>
            </div>
          </div>
        </div>

        <!-- 失败书源分析（分类展示） -->
        <FailedSources
          v-if="state.sourceData.failedCategories && Object.keys(state.sourceData.failedCategories).length > 0"
          :failed-categories="state.sourceData.failedCategories"
        />

        <!-- 失败书源分组（详细列表） -->
        <div v-if="state.sourceData.failedGroups && state.sourceData.failedGroups.length > 0" class="failed-groups">
          <h3 class="failed-title">📋 失败详情（按原因分组）</h3>
          <div class="failed-list">
            <div
              v-for="group in state.sourceData.failedGroups"
              :key="group.reason || 'unknown'"
              class="failed-item"
            >
              <div class="failed-header" @click="toggleFailedGroup(group.reason)">
                <span class="failed-reason">{{ group.reason || '未知错误' }}</span>
                <span class="failed-count">{{ group.count }} 条</span>
                <span class="failed-toggle">{{ expandedGroups[group.reason] ? '▼' : '▶' }}</span>
              </div>
              <div v-if="expandedGroups[group.reason]" class="failed-sources">
                <div
                  v-for="source in group.sources"
                  :key="source.bookSourceUrl"
                  class="failed-source-item"
                >
                  <span class="source-name">{{ source.bookSourceName || '未命名' }}</span>
                  <span class="source-url">{{ source.bookSourceUrl }}</span>
                </div>
              </div>
            </div>
          </div>
          <!-- 导出失败书源按钮 -->
          <button class="export-failed-btn" @click="handleExportFailed">
            📥 导出失败书源
          </button>
        </div>

        <DownloadButton
          :enabled="hasValidSources"
          :count="state.sourceData?.validCount || 0"
          @download="handleDownload"
        />

        <!-- 重新处理按钮 -->
        <button class="restart-btn" @click="handleClear">
          🔄 重新处理
        </button>
      </section>

      <!-- 空状态提示 -->
      <section class="empty-section" v-else-if="processMode === 'single' && !hasFile && !hasUrlData">
        <p class="empty-text">上传文件或输入链接开始处理书源</p>
        <p class="empty-hint">💡 提示：按 Ctrl+V 可直接粘贴链接解析</p>
      </section>
    </main>

    <!-- 页脚 -->
    <footer class="app-footer">
      <p class="footer-text">
        ✦ 去重基于 bookSourceUrl 字段，深度校验模拟手机端请求检测可用性
      </p>
    </footer>
  </div>
</template>

<script setup>
import FileUpload from './components/FileUpload.vue'
import UrlInput from './components/UrlInput.vue'
import ActionButtons from './components/ActionButtons.vue'
import StatsCardGroup from './components/StatsCardGroup.vue'
import DownloadButton from './components/DownloadButton.vue'
import MessageAlert from './components/MessageAlert.vue'
import ConcurrencySelector from './components/ConcurrencySelector.vue'
import TimeoutSelector from './components/TimeoutSelector.vue'
import ValidationProgress from './components/ValidationProgress.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import FilterOptions from './components/FilterOptions.vue'
import BatchProcessor from './components/BatchProcessor.vue'
import SearchValidator from './components/SearchValidator.vue'
import FailedSources from './components/FailedSources.vue'
import { useSources } from './composables/useSources.js'
import { useToast } from './composables/useToast.js'
import { parseFile, parseUrl, startValidation, startValidationFromData, getProgressEventSource, getSearchProgressEventSource, cancelValidation, startBatchFilesValidation, startBatchUrlsValidation, parseBatchFiles, parseBatchUrls, startSearchValidation } from './api/sources.js'
import { downloadJson, formatDate } from './utils/download.js'
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'

const {
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
  reset: resetState,
  clearMessages
} = useSources()

// Toast 提示
const { showSuccess, showError, showWarning, showInfo } = useToast()

// 设置（从localStorage读取）
const concurrency = ref(16)
const timeout = ref(30)
const filterTypes = ref([])
const expandedGroups = ref({})
const urlInput = ref('')
const processMode = ref('single')  // 'single' 或 'batch'
const batchProcessorRef = ref(null)

// 在线解析数据（用于支持深度校验）
const urlSourceData = ref(null)
const hasUrlData = computed(() => !!urlSourceData.value)

// SSE 相关
const progressData = ref(null)
const sessionId = ref(null)
const startResultData = ref(null)
let eventSource = null

// 耗时计算
const elapsedTime = ref(0)
let timerInterval = null

// 从localStorage读取设置
onMounted(() => {
  console.log('=== App.vue 已挂载 (版本: 2026-03-13-v2) ===')
  console.log('processMode:', processMode.value)

  const savedConcurrency = localStorage.getItem('sourceTool_concurrency')
  const savedTimeout = localStorage.getItem('sourceTool_timeout')
  if (savedConcurrency) concurrency.value = parseInt(savedConcurrency)
  if (savedTimeout) timeout.value = parseInt(savedTimeout)

  // 全局粘贴事件监听
  document.addEventListener('paste', handleGlobalPaste)
})

// 清理 SSE 连接和计时器
onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
  }
  if (timerInterval) {
    clearInterval(timerInterval)
  }
  document.removeEventListener('paste', handleGlobalPaste)
})

// 保存设置到localStorage
watch(concurrency, (val) => {
  localStorage.setItem('sourceTool_concurrency', val)
})

watch(timeout, (val) => {
  localStorage.setItem('sourceTool_timeout', val)
})

// 全局粘贴事件处理
function handleGlobalPaste(e) {
  if (state.loading || state.validating) return
  if (processMode.value !== 'single') return

  const text = e.clipboardData.getData('text')
  if (text && text.trim().startsWith('http')) {
    e.preventDefault()
    handleUrlFetch(text.trim())
  }
}

// 一键粘贴解析
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

// 切换失败分组展开状态
function toggleFailedGroup(reason) {
  expandedGroups.value[reason] = !expandedGroups.value[reason]
}

// 清除功能
function handleClear() {
  resetState()
  urlSourceData.value = null
  urlInput.value = ''
  progressData.value = null
  clearMessages()
  if (batchProcessorRef.value) {
    batchProcessorRef.value.reset()
  }
  showInfo('已清除当前数据')
}

// 处理文件上传
function handleFileUpload(file) {
  console.log('=== handleFileUpload 被调用 ===')
  console.log('file:', file)
  console.log('file.name:', file?.name)
  setFile(file)
  urlSourceData.value = null
  console.log('setFile 调用完成，state.file:', state.file)
  console.log('hasFile:', hasFile.value)
}

// 处理 URL 获取
async function handleUrlFetch(url) {
  setLoading(true)
  setError(null)
  urlInput.value = url

  const filterTypesStr = filterTypes.value.join(',')

  try {
    const result = await parseUrl(url, 'dedup', concurrency.value, timeout.value, filterTypesStr)

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

// 只查重复
async function handleDedupOnly() {
  if (state.file) {
    await handleDedupFile()
  } else if (urlSourceData.value) {
    setSourceData(urlSourceData.value)
    showSuccess(`去重完成，有效书源 ${urlSourceData.value.validCount} 条`)
  }
}

async function handleDedupFile() {
  if (!state.file) return

  setLoading(true)
  setError(null)

  const filterTypesStr = filterTypes.value.join(',')

  try {
    const result = await parseFile(state.file, 'dedup', concurrency.value, timeout.value, filterTypesStr)

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

// 开始计时
function startTimer() {
  elapsedTime.value = 0
  if (timerInterval) clearInterval(timerInterval)
  timerInterval = setInterval(() => {
    elapsedTime.value++
  }, 1000)
}

// 停止计时
function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

// 全部校验（SSE 模式）
async function handleFullValidate() {
  if (state.file) {
    await handleFullValidateFile()
  } else if (urlSourceData.value) {
    await handleFullValidateUrl()
  }
}

// 文件深度校验
async function handleFullValidateFile() {
  if (!state.file) return

  setValidating(true)
  setError(null)
  progressData.value = null
  startResultData.value = null

  const filterTypesStr = filterTypes.value.join(',')

  try {
    const startResult = await startValidation(state.file, concurrency.value, timeout.value, filterTypesStr)

    if (startResult.code !== 200) {
      showError(startResult.message)
      setValidating(false)
      return
    }

    startResultData.value = startResult
    sessionId.value = startResult.sessionId

    progressData.value = {
      processed: 0,
      total: startResult.deepTotal,
      valid: 0,
      invalid: 0,
      current: '',
      currentName: '',
      estimatedRemaining: 0
    }

    startTimer()
    eventSource = getProgressEventSource(sessionId.value)

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.error) {
        stopTimer()
        showError(data.error)
        eventSource.close()
        setValidating(false)
        return
      }

      if (data.status === 'completed' && data.validCount !== undefined) {
        stopTimer()
        eventSource.close()
        setValidating(false)

        const startData = startResultData.value
        const resultData = {
          total: startData.total,
          dedupCount: startData.dedupCount,
          duplicates: startData.duplicates,
          duplicateUrls: [],
          formatInvalid: startData.formatInvalid,
          deepInvalid: data.invalidCount,
          validCount: data.validCount,
          dedupedSources: data.validSources || [],
          failedGroups: data.failedGroups || [],
          failedCategories: data.failedCategories || {}
        }

        setSourceData(resultData)
        const invalidTotal = startData.formatInvalid + (data.invalidCount || 0)
        if (invalidTotal > 0) {
          showSuccess(`校验完成，有效 ${data.validCount} 条，失效 ${invalidTotal} 条`)
        } else {
          showSuccess(`校验完成，全部有效，共 ${data.validCount} 条`)
        }
        return
      }

      if (data.status === 'cancelled') {
        stopTimer()
        eventSource.close()
        setValidating(false)
        progressData.value = null
        showWarning('校验已取消')
        return
      }

      progressData.value = {
        processed: data.processed,
        total: data.total,
        valid: data.valid,
        invalid: data.invalid,
        current: data.current,
        currentName: data.currentName || '',
        estimatedRemaining: data.estimatedRemaining || 0
      }
    }

    eventSource.onerror = () => {
      stopTimer()
      eventSource.close()
      showError('连接中断，请重试')
      setValidating(false)
    }

  } catch (err) {
    stopTimer()
    showError('校验失败，请稍后重试')
    setValidating(false)
  }
}

// 在线解析深度校验
async function handleFullValidateUrl() {
  if (!urlSourceData.value) return

  setValidating(true)
  setError(null)
  progressData.value = {
    processed: 0,
    total: urlSourceData.value.dedupedSources?.length || 0,
    valid: 0,
    invalid: 0,
    current: '',
    currentName: '',
    estimatedRemaining: 0
  }

  startTimer()

  try {
    const result = await startValidationFromData(
      urlSourceData.value.dedupedSources || [],
      concurrency.value,
      timeout.value
    )

    if (result.code !== 200) {
      showError(result.message)
      setValidating(false)
      stopTimer()
      return
    }

    sessionId.value = result.sessionId
    eventSource = getProgressEventSource(sessionId.value)

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.error) {
        stopTimer()
        showError(data.error)
        eventSource.close()
        setValidating(false)
        return
      }

      if (data.status === 'completed' && data.validCount !== undefined) {
        stopTimer()
        eventSource.close()
        setValidating(false)

        const resultData = {
          total: urlSourceData.value.total,
          dedupCount: urlSourceData.value.dedupCount,
          duplicates: urlSourceData.value.duplicates,
          duplicateUrls: [],
          formatInvalid: urlSourceData.value.formatInvalid,
          deepInvalid: data.invalidCount,
          validCount: data.validCount,
          dedupedSources: data.validSources || [],
          failedGroups: data.failedGroups || [],
          failedCategories: data.failedCategories || {}
        }

        setSourceData(resultData)
        const invalidTotal = urlSourceData.value.formatInvalid + (data.invalidCount || 0)
        if (invalidTotal > 0) {
          setSuccess(`校验完成！有效书源 ${data.validCount} 条，失效 ${invalidTotal} 条，耗时 ${elapsedTime.value} 秒`)
        } else {
          setSuccess(`校验完成！有效书源 ${data.validCount} 条，耗时 ${elapsedTime.value} 秒`)
        }
        return
      }

      if (data.status === 'cancelled') {
        stopTimer()
        eventSource.close()
        setValidating(false)
        progressData.value = null
        showWarning('校验已取消')
        return
      }

      progressData.value = {
        processed: data.processed,
        total: data.total,
        valid: data.valid,
        invalid: data.invalid,
        current: data.current,
        currentName: data.currentName || '',
        estimatedRemaining: data.estimatedRemaining || 0
      }
    }

    eventSource.onerror = () => {
      stopTimer()
      eventSource.close()
      showError('连接中断，请重试')
      setValidating(false)
    }

  } catch (err) {
    stopTimer()
    showError('校验失败，请稍后重试')
    setValidating(false)
  }
}

// 批量处理
async function handleBatchProcess({ type, data, mode }) {
  setError(null)

  const filterTypesStr = filterTypes.value.join(',')

  // 批量去重模式 - 直接请求
  if (mode === 'dedup') {
    setLoading(true)
    try {
      let result
      if (type === 'files') {
        result = await parseBatchFiles(data, 'dedup', concurrency.value, timeout.value, filterTypesStr)
      } else {
        result = await parseBatchUrls(data, 'dedup', concurrency.value, timeout.value, filterTypesStr)
      }

      if (result.code !== 200) {
        showError(result.message)
        return
      }

      // 更新批量统计
      if (batchProcessorRef.value) {
        batchProcessorRef.value.setStats({
          fileStats: result.data.fileStats,
          urlStats: result.data.urlStats
        })
      }

      setSourceData(result.data)
      setSuccess(`批量去重完成！有效书源 ${result.data.validCount} 条`)
    } catch (err) {
      showError('批量处理失败，请稍后重试')
    } finally {
      setLoading(false)
    }
    return
  }

  // 批量校验模式 - 使用 SSE
  setValidating(true)
  progressData.value = null
  startResultData.value = null

  try {
    let startResult
    if (type === 'files') {
      startResult = await startBatchFilesValidation(data, concurrency.value, timeout.value, filterTypesStr)
    } else {
      startResult = await startBatchUrlsValidation(data, concurrency.value, timeout.value, filterTypesStr)
    }

    if (startResult.code !== 200) {
      showError(startResult.message)
      setValidating(false)
      return
    }

    startResultData.value = startResult
    sessionId.value = startResult.sessionId

    progressData.value = {
      processed: 0,
      total: startResult.deepTotal,
      valid: 0,
      invalid: 0,
      current: '',
      currentName: '',
      estimatedRemaining: 0
    }

    // 更新批量统计
    if (batchProcessorRef.value) {
      batchProcessorRef.value.setStats({
        fileStats: startResult.fileStats,
        urlStats: startResult.urlStats
      })
    }

    startTimer()
    eventSource = getProgressEventSource(sessionId.value)

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.error) {
        stopTimer()
        showError(data.error)
        eventSource.close()
        setValidating(false)
        return
      }

      if (data.status === 'completed' && data.validCount !== undefined) {
        stopTimer()
        eventSource.close()
        setValidating(false)

        const resultData = {
          total: data.totalOriginal || startResult.total,
          dedupCount: data.dedupCount || startResult.deepTotal,
          duplicates: data.duplicates || 0,
          duplicateUrls: [],
          formatInvalid: data.formatInvalid || 0,
          deepInvalid: data.invalidCount,
          validCount: data.validCount,
          dedupedSources: data.validSources || [],
          failedGroups: data.failedGroups || [],
          failedCategories: data.failedCategories || {}
        }

        setSourceData(resultData)
        const invalidTotal = (data.formatInvalid || 0) + (data.invalidCount || 0)
        if (invalidTotal > 0) {
          setSuccess(`校验完成！有效书源 ${data.validCount} 条，失效 ${invalidTotal} 条，耗时 ${elapsedTime.value} 秒`)
        } else {
          setSuccess(`校验完成！有效书源 ${data.validCount} 条，耗时 ${elapsedTime.value} 秒`)
        }
        return
      }

      if (data.status === 'cancelled') {
        stopTimer()
        eventSource.close()
        setValidating(false)
        progressData.value = null
        showWarning('校验已取消')
        return
      }

      progressData.value = {
        processed: data.processed,
        total: data.total,
        valid: data.valid,
        invalid: data.invalid,
        current: data.current,
        currentName: data.currentName || '',
        estimatedRemaining: data.estimatedRemaining || 0
      }
    }

    eventSource.onerror = () => {
      stopTimer()
      eventSource.close()
      showError('连接中断，请重试')
      setValidating(false)
    }

  } catch (err) {
    stopTimer()
    showError('批量校验失败，请稍后重试')
    setValidating(false)
  }
}

// 取消校验
async function handleCancelValidation() {
  if (!sessionId.value) return

  try {
    await cancelValidation(sessionId.value)
    if (eventSource) {
      eventSource.close()
    }
    stopTimer()
    setValidating(false)
    progressData.value = null
    showWarning('校验已取消')
  } catch (err) {
    showError('取消失败')
  }
}

// 搜索校验
async function handleSearchValidation(payload) {
  console.log('=== handleSearchValidation 被调用 ===')
  console.log('payload:', payload)
  console.log('state.file:', state.file)

  const { validateType, keyword, concurrency: searchConcurrency, timeout: searchTimeout } = payload

  if (!state.file) {
    console.error('state.file 为空，无法开始校验')
    showError('请先上传书源文件')
    return
  }

  console.log('开始搜索校验，参数:', { validateType, keyword, searchConcurrency, searchTimeout })

  setValidating(true)
  setError(null)
  progressData.value = null

  try {
    console.log('调用 startSearchValidation API...')
    const startResult = await startSearchValidation(
      state.file,
      keyword,
      validateType,
      searchConcurrency || 16,
      searchTimeout || 30
    )

    console.log('startSearchValidation 返回结果:', startResult)

    if (startResult.code !== 200) {
      showError(startResult.message)
      setValidating(false)
      return
    }

    sessionId.value = startResult.sessionId
    console.log('搜索校验会话创建成功:', startResult)

    progressData.value = {
      processed: 0,
      total: startResult.total,
      valid: 0,
      invalid: 0,
      current: '',
      currentName: '',
      estimatedRemaining: 0
    }

    startTimer()
    console.log('准备建立 SSE 连接:', `/api/validate/search/progress/${sessionId.value}`)

    try {
      eventSource = getSearchProgressEventSource(sessionId.value)
      console.log('EventSource 创建完成:', eventSource)
      console.log('EventSource readyState:', eventSource.readyState)
      console.log('EventSource url:', eventSource.url)
    } catch (esError) {
      console.error('EventSource 创建失败:', esError)
      throw esError
    }

    eventSource.onopen = (event) => {
      console.log('SSE 连接已打开:', event)
    }

    eventSource.onmessage = (event) => {
      console.log('SSE 消息:', event.data)
      const data = JSON.parse(event.data)

      if (data.error) {
        stopTimer()
        showError(data.error)
        eventSource.close()
        setValidating(false)
        return
      }

      if (data.status === 'completed' && data.validCount !== undefined) {
        stopTimer()
        eventSource.close()
        setValidating(false)

        const resultData = {
          total: startResult.total,
          dedupCount: startResult.total,
          duplicates: 0,
          duplicateUrls: [],
          formatInvalid: 0,
          deepInvalid: data.invalidCount,
          validCount: data.validCount,
          dedupedSources: data.validSources || [],
          failedGroups: data.failedGroups || [],
          failedCategories: data.failedCategories || {},
          ruleTypeStats: data.ruleTypeStats || null
        }

        setSourceData(resultData)
        const typeLabel = validateType === 'search' ? '搜索' : '发现'
        if (data.invalidCount > 0) {
          setSuccess(`${typeLabel}校验完成！有效书源 ${data.validCount} 条，失效 ${data.invalidCount} 条，耗时 ${elapsedTime.value} 秒`)
        } else {
          setSuccess(`${typeLabel}校验完成！有效书源 ${data.validCount} 条，耗时 ${elapsedTime.value} 秒`)
        }
        return
      }

      if (data.status === 'cancelled') {
        stopTimer()
        eventSource.close()
        setValidating(false)
        progressData.value = null
        showWarning('校验已取消')
        return
      }

      progressData.value = {
        processed: data.processed,
        total: data.total,
        valid: data.valid,
        invalid: data.invalid,
        current: data.current,
        currentName: data.currentName || '',
        estimatedRemaining: data.estimatedRemaining || 0
      }
    }

    eventSource.onerror = () => {
      console.error('搜索校验 SSE 连接错误')
      stopTimer()
      eventSource.close()
      showError('连接中断，请重试')
      setValidating(false)
    }

  } catch (err) {
    console.error('搜索校验异常:', err)
    stopTimer()
    showError('搜索校验失败，请稍后重试')
    setValidating(false)
  }
}

// 处理下载
function handleDownload() {
  if (!state.sourceData?.dedupedSources) return

  downloadJson(
    state.sourceData.dedupedSources,
    `阅读书源_去重有效_${formatDate(new Date())}.json`
  )
  showSuccess('已下载有效书源文件')
}

// 导出失败书源
function handleExportFailed() {
  if (!state.sourceData?.failedGroups) return

  const failedSources = []
  for (const group of state.sourceData.failedGroups) {
    for (const source of group.sources) {
      // 复制完整书源信息，移除内部字段
      const exportSource = { ...source }
      delete exportSource._failureReason
      delete exportSource._ruleType
      // 添加失败原因分组
      exportSource._failureGroup = group.reason || '未知错误'
      failedSources.push(exportSource)
    }
  }

  downloadJson(
    failedSources,
    `阅读书源_失败列表_${formatDate(new Date())}.json`
  )
  showSuccess(`已导出 ${failedSources.length} 条失败书源`)
}
</script>

<style>
/* 规则类型统计样式 */
.rule-type-stats {
  margin-top: 20px;
  padding: 16px;
  background: var(--card-bg);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.rule-type-title {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: var(--text-primary);
}

.rule-type-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.rule-type-card {
  padding: 12px;
  border-radius: 8px;
  text-align: center;
}

.rule-type-card.search-only {
  background: rgba(64, 158, 255, 0.1);
  border: 1px solid rgba(64, 158, 255, 0.3);
}

.rule-type-card.explore-only {
  background: rgba(103, 194, 58, 0.1);
  border: 1px solid rgba(103, 194, 58, 0.3);
}

.rule-type-card.both {
  background: rgba(230, 162, 60, 0.1);
  border: 1px solid rgba(230, 162, 60, 0.3);
}

.rule-type-card.none {
  background: rgba(245, 108, 108, 0.1);
  border: 1px solid rgba(245, 108, 108, 0.3);
}

.rule-type-label {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.rule-type-numbers {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-bottom: 4px;
  font-size: 13px;
}

.rule-type-numbers .valid {
  color: #67c23a;
}

.rule-type-numbers .invalid {
  color: #f56c6c;
}

.rule-type-total {
  font-size: 12px;
  color: var(--text-muted);
}

/* 失败分组样式 */
.failed-groups {
  margin-top: 20px;
  padding: 16px;
  background: var(--failed-bg);
  border-radius: 8px;
  border: 1px solid var(--failed-border);
}

.failed-title {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: var(--failed-text);
}

.failed-list {
  max-height: 300px;
  overflow-y: auto;
}

.failed-item {
  border-bottom: 1px solid var(--failed-border);
}

.failed-item:last-child {
  border-bottom: none;
}

.failed-header {
  display: flex;
  align-items: center;
  padding: 12px 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.failed-header:hover {
  background: var(--bg-tertiary);
}

.failed-reason {
  flex: 1;
  font-weight: 500;
  color: var(--failed-text);
}

.failed-count {
  margin-right: 12px;
  color: var(--text-secondary);
  font-size: 14px;
}

.failed-toggle {
  color: var(--text-muted);
  font-size: 12px;
}

.failed-sources {
  padding: 8px 16px 12px;
  background: var(--card-bg);
}

.failed-source-item {
  display: flex;
  flex-direction: column;
  padding: 8px 0;
  border-bottom: 1px dashed var(--border-light);
}

.failed-source-item:last-child {
  border-bottom: none;
}

.source-name {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.source-url {
  font-size: 12px;
  color: var(--text-muted);
  word-break: break-all;
}

.export-failed-btn {
  margin-top: 16px;
  width: 100%;
  padding: 10px;
  background: #ef5350;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.export-failed-btn:hover {
  background: #d32f2f;
}

/* 设置区域 */
.settings-section {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 16px;
}

/* 空状态提示 */
.empty-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

/* 模式切换 */
.mode-switch {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  justify-content: center;
}

.mode-btn {
  padding: 10px 20px;
  border: 2px solid var(--border-color);
  background: var(--card-bg);
  color: var(--text-secondary);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.mode-btn:hover {
  border-color: #409eff;
  color: var(--text-primary);
}

.mode-btn.active {
  border-color: #409eff;
  background: var(--bg-tertiary);
  color: #409eff;
  font-weight: 500;
}

/* 清除按钮 */
.clear-btn {
  display: block;
  margin: 0 auto 16px;
  padding: 8px 20px;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.clear-btn:hover:not(:disabled) {
  color: #f56c6c;
  border-color: #f56c6c;
}

.clear-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 重新处理按钮 */
.restart-btn {
  display: block;
  margin: 16px auto 0;
  padding: 12px 24px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 2px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.restart-btn:hover {
  border-color: #409eff;
  color: #409eff;
}

/* 移动端模式切换 */
@media (max-width: 575px) {
  .mode-switch {
    gap: 6px;
  }

  .mode-btn {
    padding: 8px 16px;
    font-size: 13px;
  }
}
</style>
