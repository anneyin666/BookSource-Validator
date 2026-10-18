<template>
  <div class="app-container">
    <!-- 主题切换按钮 -->
    <FeedbackButton />
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

      <div v-if="isMobileBrowser" class="mobile-session-warning">
        手机校验时请保持本页面在前台，锁屏、切到后台或浏览器省电可能中断进度连接。
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
          <ValidationPresetSelector v-model="validationMode" @apply="applyValidationPreset" />
          <div v-if="validationMode === 'custom'" class="custom-strategy-fields">
            <ConcurrencySelector v-model="concurrency" />
            <TimeoutSelector v-model="timeout" />
          </div>
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
          <ValidationPresetSelector v-model="validationMode" @apply="applyValidationPreset" />
          <div v-if="validationMode === 'custom'" class="custom-strategy-fields">
            <ConcurrencySelector v-model="concurrency" />
            <TimeoutSelector v-model="timeout" />
          </div>
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
        :status="progressData.status || 'running'"
        :strategy="progressData.strategy || null"
        :requested-mode="validationMode"
        @pause="handlePauseValidation"
        @resume="handleResumeValidation"
        @cancel="handleCancelValidation"
      />

      <!-- 统计结果 -->
      <ResultPanel
        v-if="state.sourceData"
        :source-data="state.sourceData"
        :stats="stats"
        :process-mode="processMode"
        :has-valid-sources="hasValidSources"
        :expanded-groups="expandedGroups"
        :legado-export="legadoExport"
        :legado-export-expire-text="legadoExportExpireText"
        @toggle-group="toggleFailedGroup"
        @retry-failed="handleRetryFailed"
        @export-failed="handleExportFailed"
        @download="handleDownload"
        @export-app="handleExportToLegado"
        @restart="handleClear"
      />

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
import ResultPanel from './components/ResultPanel.vue'
import MessageAlert from './components/MessageAlert.vue'
import ConcurrencySelector from './components/ConcurrencySelector.vue'
import TimeoutSelector from './components/TimeoutSelector.vue'
import ValidationPresetSelector from './components/ValidationPresetSelector.vue'
import ValidationProgress from './components/ValidationProgress.vue'
import FeedbackButton from './components/FeedbackButton.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import FilterOptions from './components/FilterOptions.vue'
import BatchProcessor from './components/BatchProcessor.vue'
import SearchValidator from './components/SearchValidator.vue'
import { useSources } from './composables/useSources.js'
import { useToast } from './composables/useToast.js'
import { useLegadoExport } from './composables/useLegadoExport.js'
import { useFailedRetry } from './composables/useFailedRetry.js'
import { useBatchProcess } from './composables/useBatchProcess.js'
import { useSingleProcess } from './composables/useSingleProcess.js'
import { useSearchValidation } from './composables/useSearchValidation.js'
import { cancelValidation, pauseValidation, resumeValidation } from './api/sources.js'
import { downloadJson, formatDate, openExternalUrl } from './utils/download.js'
import { useSSEValidation } from './composables/useSSEValidation.js'
import { ref, onMounted, watch, onUnmounted } from 'vue'

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
const validationMode = ref('balanced')
const filterTypes = ref([])
const expandedGroups = ref({})
const processMode = ref('single')  // 'single' 或 'batch'
const batchProcessorRef = ref(null)
const isMobileBrowser = ref(false)

// 导出到阅读 App（临时链接生成/缓存/过期提示）
const {
  legadoExport,
  legadoExportExpireText,
  reset: resetLegadoExport,
  getCached: getCachedLegadoExport,
  ensureReady: ensureLegadoExportReady
} = useLegadoExport({
  getSources: () => state.sourceData?.dedupedSources || [],
  getValidCount: () => state.sourceData?.validCount || 0,
  showError,
  showWarning
})

// SSE 相关
const sessionId = ref(null)
const startResultData = ref(null)

// 统一的 SSE 校验订阅（含进度解析、断线恢复与强制重连看门狗）
const {
  progressData,
  elapsedTime,
  subscribe: subscribeValidation,
  stop: stopValidation,
  destroy: destroyValidation
} = useSSEValidation({
  onDisconnect: (label) => showWarning(`${label}连接暂时中断，正在自动恢复，服务器仍在校验`),
  onReconnect: (label) => showSuccess(`${label}连接已恢复`)
})

// 批量处理流程（批量去重 / 批量校验）
const { handleBatchProcess } = useBatchProcess({
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
})

// 单个处理流程（文件/在线链接的去重与深度校验）
const {
  urlInput,
  hasUrlData,
  handleFileUpload,
  handleUrlFetch,
  handleDedupOnly,
  handleFullValidate,
  handleGlobalPaste,
  pasteAndParse,
  reset: resetSingleProcess
} = useSingleProcess({
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
  isSingleMode: () => processMode.value === 'single'
})

// 搜索校验流程
const { lastSearchConfig, handleSearchValidation } = useSearchValidation({
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
})

// 失败重试（纯逻辑 + 重试会话编排）
const { handleRetryFailed } = useFailedRetry({
  state,
  setValidating,
  setSourceData,
  progressData,
  subscribeValidation,
  stopValidation,
  concurrency,
  timeout,
  validationMode,
  sessionId,
  processMode,
  lastSearchConfig,
  showSuccess,
  showWarning,
  showError
})

// 从localStorage读取设置
onMounted(() => {
  isMobileBrowser.value = /android|iphone|ipad|ipod|mobile/i.test(window.navigator.userAgent)

  const savedConcurrency = localStorage.getItem('sourceTool_concurrency')
  const savedTimeout = localStorage.getItem('sourceTool_timeout')
  if (savedConcurrency) concurrency.value = parseInt(savedConcurrency)
  if (savedTimeout) timeout.value = parseInt(savedTimeout)
  localStorage.removeItem('sourceTool_validationMode')

  // 全局粘贴事件监听
  document.addEventListener('paste', handleGlobalPaste)
})

// 清理 SSE 连接和全局监听
onUnmounted(() => {
  destroyValidation()
  document.removeEventListener('paste', handleGlobalPaste)
})

// 保存设置到localStorage
watch(concurrency, (val) => {
  localStorage.setItem('sourceTool_concurrency', val)
})

watch(timeout, (val) => {
  localStorage.setItem('sourceTool_timeout', val)
})

watch(() => state.sourceData?.dedupedSources, (sources) => {
  resetLegadoExport()

  if (Array.isArray(sources) && sources.length > 0 && isMobileBrowser.value) {
    void ensureLegadoExportReady({ silent: true })
  }
})

function applyValidationPreset(preset) {
  if (preset.value === 'custom') return
  concurrency.value = preset.concurrency
  timeout.value = preset.timeout
}

// 切换失败分组展开状态
function toggleFailedGroup(reason) {
  expandedGroups.value[reason] = !expandedGroups.value[reason]
}

// 清除功能
function handleClear() {
  resetState()
  resetSingleProcess()
  progressData.value = null
  resetLegadoExport()
  clearMessages()
  if (batchProcessorRef.value) {
    batchProcessorRef.value.reset()
  }
  showInfo('已清除当前数据')
}

// 取消校验
async function handleCancelValidation() {
  if (!sessionId.value) return

  try {
    await cancelValidation(sessionId.value)
    showWarning('正在取消校验，已完成结果会保留...')
  } catch (err) {
    showError('取消失败')
  }
}

async function handlePauseValidation() {
  if (!sessionId.value) return

  try {
    await pauseValidation(sessionId.value)
    if (progressData.value) {
      progressData.value.status = 'paused'
    }
    showInfo('校验已暂停，已发出的请求会先完成')
  } catch (err) {
    showError('暂停失败')
  }
}

async function handleResumeValidation() {
  if (!sessionId.value) return

  try {
    await resumeValidation(sessionId.value)
    if (progressData.value) {
      progressData.value.status = 'running'
    }
    showInfo('校验已继续')
  } catch (err) {
    showError('继续失败')
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

async function handleExportToLegado() {
  if (!hasValidSources.value) return

  const exportInfo = getCachedLegadoExport() || await ensureLegadoExportReady()
  if (!exportInfo) return

  if (!isMobileBrowser.value) {
    showInfo('已生成临时导出链接。这个入口主要给手机浏览器使用，你也可以直接打开下方链接。')
    return
  }

  openExternalUrl(exportInfo.legadoUrl)
  showInfo('已尝试唤起阅读 App；若未自动跳转，请确认已安装阅读，并尝试打开下方临时链接。')
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
/* 设置区域 */
.settings-section {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 16px;
}

.settings-section > * {
  flex: 1 1 260px;
}

.settings-section > .preset-selector {
  flex-basis: 100%;
}

.custom-strategy-fields {
  display: flex;
  justify-content: center;
  gap: 10px;
  flex: 1 1 220px;
}

.mobile-session-warning {
  max-width: 720px;
  margin: -4px auto 16px;
  padding: 10px 12px;
  border: 1px solid rgba(230, 162, 60, 0.35);
  border-radius: 8px;
  background: rgba(230, 162, 60, 0.1);
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
  text-align: center;
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
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
  justify-content: center;
}

.mode-btn {
  min-width: 140px;
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

@media (max-width: 575px) {
  .settings-section {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    align-items: stretch;
  }

  .settings-section > * {
    min-width: 0;
    flex: none;
  }

  .settings-section > .filter-options {
    grid-column: 1 / -1;
  }

  .settings-section > .preset-selector {
    grid-column: 1 / -1;
  }

  .custom-strategy-fields {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .settings-section > .concurrency-selector,
  .settings-section > .timeout-selector,
  .custom-strategy-fields > .concurrency-selector,
  .custom-strategy-fields > .timeout-selector {
    justify-content: center;
    padding: 10px 8px;
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
  }
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

/* 移动端模式切换 */
@media (max-width: 575px) {
  .mode-switch {
    gap: 6px;
  }

  .mode-btn {
    flex: 1 1 calc(50% - 6px);
    padding: 8px 16px;
    font-size: 13px;
  }
}
</style>
