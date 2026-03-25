<template>
  <div class="batch-processor">
    <div class="batch-tabs">
      <button
        :class="['tab-btn', { active: activeTab === 'files' }]"
        @click="activeTab = 'files'"
      >
        📁 批量文件
      </button>
      <button
        :class="['tab-btn', { active: activeTab === 'urls' }]"
        @click="activeTab = 'urls'"
      >
        🔗 批量链接
      </button>
    </div>

    <!-- 批量文件上传 -->
    <div v-if="activeTab === 'files'" class="batch-section">
      <div
        class="batch-drop-zone"
        :class="{ 'is-dragging': isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleFileDrop"
        @click="triggerFileSelect"
      >
        <div class="drop-icon">📂</div>
        <p class="drop-text">拖拽多个文件到此处，或点击选择</p>
        <p class="drop-hint">支持同时上传多个 .json、.txt 文件</p>
        <input
          ref="fileInput"
          type="file"
          accept=".json,.txt,application/json,text/plain"
          multiple
          hidden
          @change="handleFileSelect"
        />
      </div>

      <!-- 已选择的文件列表 -->
      <div v-if="selectedFiles.length > 0" class="selected-list">
        <div class="list-header">
          <span>已选择 {{ selectedFiles.length }} 个文件</span>
          <button class="clear-btn" @click="clearFiles">清空</button>
        </div>
        <div class="file-list">
          <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatSize(file.size) }}</span>
            <button class="remove-btn" @click="removeFile(index)">✕</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 批量URL输入 -->
    <div v-if="activeTab === 'urls'" class="batch-section">
      <textarea
        v-model="urlInput"
        class="url-textarea"
        placeholder="输入多个书源链接，每行一个&#10;例如：&#10;https://example.com/source1.json&#10;https://example.com/source2.json"
        rows="6"
      ></textarea>
      <p class="url-hint">每行一个URL，自动识别并解析</p>
    </div>

    <!-- 批量处理统计 -->
    <div v-if="batchStats" class="batch-stats">
      <div class="stats-header">📊 批量处理统计</div>
      <div class="stats-grid">
        <div v-if="batchStats.fileStats" class="stats-group">
          <div class="stats-title">文件统计</div>
          <div v-for="(stat, index) in batchStats.fileStats" :key="index" class="stat-item">
            <span class="stat-name">{{ stat.name }}</span>
            <span :class="['stat-status', stat.valid ? 'valid' : 'invalid']">
              {{ stat.valid ? `${stat.count} 条` : stat.error }}
            </span>
          </div>
        </div>
        <div v-if="batchStats.urlStats" class="stats-group">
          <div class="stats-title">URL统计</div>
          <div v-for="(stat, index) in batchStats.urlStats" :key="index" class="stat-item">
            <span class="stat-name">{{ truncateUrl(stat.url) }}</span>
            <span :class="['stat-status', stat.valid ? 'valid' : 'invalid']">
              {{ stat.valid ? `${stat.count} 条` : stat.error }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div v-if="hasItems && !batchStats" class="batch-actions">
      <button
        class="action-btn primary"
        :disabled="loading"
        @click="handleBatchDedup"
      >
        <span v-if="loading && loadingMode === 'dedup'" class="loading-spinner"></span>
        🔍 批量去重
      </button>
      <button
        class="action-btn secondary"
        :disabled="loading"
        @click="handleBatchValidate"
      >
        <span v-if="loading && loadingMode === 'validate'" class="loading-spinner"></span>
        ✅ 批量校验
      </button>
    </div>

    <!-- 清除按钮（处理后显示） -->
    <button v-if="batchStats" class="reset-btn" @click="reset">
      🗑️ 清除重新处理
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  loading: Boolean,
  concurrency: { type: Number, default: 16 },
  timeout: { type: Number, default: 30 },
  filterTypes: { type: Array, default: () => [] }
})

const emit = defineEmits(['batch-process'])

const activeTab = ref('files')
const selectedFiles = ref([])
const urlInput = ref('')
const isDragging = ref(false)
const fileInput = ref(null)
const batchStats = ref(null)
const loadingMode = ref('') // 'dedup' 或 'validate'

const hasItems = computed(() => {
  if (activeTab.value === 'files') {
    return selectedFiles.value.length > 0
  }
  return urlInput.value.trim().length > 0
})

function triggerFileSelect() {
  if (props.loading) return
  fileInput.value?.click()
}

function handleFileSelect(event) {
  const files = Array.from(event.target.files || [])
  addFiles(files)
  event.target.value = '' // 重置以允许重复选择同一文件
}

function handleFileDrop(event) {
  isDragging.value = false
  const files = Array.from(event.dataTransfer?.files || [])
  addFiles(files)
}

function addFiles(files) {
  const validFiles = files.filter(f => {
    const lowerName = f.name.toLowerCase()
    return lowerName.endsWith('.json') || lowerName.endsWith('.txt') || f.type === 'application/json'
  })
  if (validFiles.length !== files.length) {
    alert('部分文件不是 JSON/TXT 格式，已忽略')
  }
  selectedFiles.value = [...selectedFiles.value, ...validFiles]
}

function removeFile(index) {
  selectedFiles.value.splice(index, 1)
}

function clearFiles() {
  selectedFiles.value = []
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function truncateUrl(url) {
  if (!url) return ''
  if (url.length > 40) return url.substring(0, 40) + '...'
  return url
}

function getUrls() {
  return urlInput.value
    .split('\n')
    .map(u => u.trim())
    .filter(u => u.startsWith('http://') || u.startsWith('https://'))
}

function handleBatchDedup() {
  loadingMode.value = 'dedup'
  processBatch('dedup')
}

function handleBatchValidate() {
  loadingMode.value = 'validate'
  processBatch('full')
}

function processBatch(mode) {
  if (activeTab.value === 'files') {
    emit('batch-process', {
      type: 'files',
      data: selectedFiles.value,
      mode
    })
  } else {
    const urls = getUrls()
    if (urls.length === 0) {
      alert('请输入有效的URL')
      return
    }
    emit('batch-process', {
      type: 'urls',
      data: urls,
      mode
    })
  }
}

// 设置统计信息
function setStats(stats) {
  batchStats.value = stats
  loadingMode.value = '' // 处理完成，清除加载模式
}

// 重置组件
function reset() {
  selectedFiles.value = []
  urlInput.value = ''
  batchStats.value = null
  loadingMode.value = ''
}

defineExpose({ setStats, reset })
</script>

<style scoped>
.batch-processor {
  background: var(--card-bg);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
}

.batch-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tab-btn {
  flex: 1;
  padding: 10px 16px;
  border: 2px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.tab-btn:hover {
  border-color: #409eff;
  color: var(--text-primary);
}

.tab-btn.active {
  border-color: #409eff;
  background: var(--bg-tertiary);
  color: #409eff;
  font-weight: 500;
}

.batch-section {
  margin-bottom: 16px;
}

.batch-drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  background: var(--bg-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.batch-drop-zone:hover,
.batch-drop-zone.is-dragging {
  border-color: #409eff;
  background: var(--bg-tertiary);
}

.drop-icon {
  font-size: 36px;
  margin-bottom: 12px;
}

.drop-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.drop-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.selected-list {
  margin-top: 12px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-radius: 6px 6px 0 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.clear-btn {
  padding: 4px 8px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 12px;
}

.clear-btn:hover {
  color: #f56c6c;
  border-color: #f56c6c;
}

.file-list {
  max-height: 150px;
  overflow-y: auto;
  border: 1px solid var(--border-light);
  border-top: none;
  border-radius: 0 0 6px 6px;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-light);
  font-size: 13px;
}

.file-item:last-child {
  border-bottom: none;
}

.file-name {
  flex: 1;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  margin-right: 12px;
  color: var(--text-muted);
  font-size: 12px;
}

.remove-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 4px;
}

.remove-btn:hover {
  background: #fef0f0;
  color: #f56c6c;
}

.url-textarea {
  width: 100%;
  padding: 12px;
  border: 2px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
}

.url-textarea:focus {
  outline: none;
  border-color: #409eff;
}

.url-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.batch-stats {
  margin-top: 16px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.stats-header {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.stats-group {
  background: var(--card-bg);
  padding: 12px;
  border-radius: 6px;
}

.stats-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 12px;
}

.stat-name {
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 8px;
}

.stat-status {
  white-space: nowrap;
}

.stat-status.valid {
  color: #67c23a;
}

.stat-status.invalid {
  color: #f56c6c;
}

.batch-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.action-btn {
  flex: 1;
  padding: 12px 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.action-btn.primary {
  background: #409eff;
  color: white;
}

.action-btn.primary:hover:not(:disabled) {
  background: #66b1ff;
}

.action-btn.secondary {
  background: #67c23a;
  color: white;
}

.action-btn.secondary:hover:not(:disabled) {
  background: #85ce61;
}

.reset-btn {
  display: block;
  margin: 16px auto 0;
  padding: 10px 20px;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.reset-btn:hover {
  color: #f56c6c;
  border-color: #f56c6c;
}

/* 加载动画 */
.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 移动端适配 */
@media (max-width: 575px) {
  .batch-processor {
    padding: 12px;
  }

  .batch-tabs {
    gap: 6px;
  }

  .tab-btn {
    padding: 8px 12px;
    font-size: 13px;
  }

  .batch-drop-zone {
    padding: 24px 12px;
  }

  .drop-icon {
    font-size: 32px;
  }

  .drop-text {
    font-size: 13px;
  }

  .list-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .file-item {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto auto;
    gap: 8px;
    align-items: center;
  }

  .file-name,
  .stat-name {
    white-space: normal;
    word-break: break-all;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .stat-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .batch-actions {
    flex-direction: column;
    gap: 8px;
  }

  .action-btn {
    min-height: 44px;
  }
}
</style>
