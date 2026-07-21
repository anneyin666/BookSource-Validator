<template>
  <div class="progress-container">
    <div class="progress-header">
      <span class="progress-title">🔍 深度校验进行中...</span>
      <span class="progress-count">{{ processed }} / {{ total }}</span>
    </div>

    <el-progress
      :percentage="percentage"
      :stroke-width="20"
      :show-text="false"
      class="progress-bar"
    />

    <div class="progress-stats">
      <span class="stat-item valid">✅ 有效: {{ valid }}</span>
      <span class="stat-item invalid">❌ 失败: {{ invalid }}</span>
      <span class="stat-item time">⏱️ 耗时: {{ formatTime(elapsedTime) }}</span>
      <span class="stat-item strategy" v-if="strategy">
        🧠 {{ strategyLabel }}
      </span>
      <span class="stat-item estimate" v-if="estimatedRemaining > 0">
        📊 预估剩余: {{ formatTime(estimatedRemaining) }}
      </span>
    </div>

    <div class="progress-current" v-if="currentUrl || currentName">
      <span class="current-label">当前:</span>
      <span class="current-name" v-if="currentName">{{ truncateText(currentName, 20) }}</span>
      <span class="current-url" v-if="currentUrl">{{ truncateUrl(currentUrl) }}</span>
    </div>

    <div class="progress-actions">
      <button v-if="status === 'paused'" class="resume-btn" @click="$emit('resume')">
        ▶️ 继续校验
      </button>
      <button v-else class="pause-btn" @click="$emit('pause')">
        ⏸️ 暂停校验
      </button>
      <button class="cancel-btn" @click="$emit('cancel')">
        ⏹️ 取消并保留结果
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  processed: {
    type: Number,
    default: 0
  },
  total: {
    type: Number,
    default: 100
  },
  valid: {
    type: Number,
    default: 0
  },
  invalid: {
    type: Number,
    default: 0
  },
  currentUrl: {
    type: String,
    default: ''
  },
  currentName: {
    type: String,
    default: ''
  },
  elapsedTime: {
    type: Number,
    default: 0
  },
  estimatedRemaining: {
    type: Number,
    default: 0
  },
  status: {
    type: String,
    default: 'running'
  },
  strategy: {
    type: Object,
    default: null
  }
})

defineEmits(['cancel', 'pause', 'resume'])

const percentage = computed(() => {
  if (props.total === 0) return 0
  return Math.round((props.processed / props.total) * 100)
})

const strategyLabel = computed(() => {
  if (!props.strategy) return ''
  const modeMap = {
    fast: '快速',
    balanced: '均衡',
    stable: '稳定',
    custom: '自定义'
  }
  const phaseMap = {
    primary: '首轮',
    retry: '网络重试'
  }
  const mode = modeMap[props.strategy.mode] || props.strategy.mode || '策略'
  const phase = phaseMap[props.strategy.phase] || ''
  const phaseText = phase ? ` · ${phase}` : ''
  return `${mode}${phaseText} · ${props.strategy.currentConcurrency || '-'}并发 · ${props.strategy.currentTimeout || '-'}秒`
})

function truncateUrl(url) {
  if (!url) return ''
  if (url.length > 40) {
    return url.substring(0, 40) + '...'
  }
  return url
}

function truncateText(text, maxLen) {
  if (!text) return ''
  if (text.length > maxLen) {
    return text.substring(0, maxLen) + '...'
  }
  return text
}

function formatTime(seconds) {
  if (seconds < 60) {
    return `${Math.round(seconds)}秒`
  }
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}分${secs}秒`
}
</script>

<style scoped>
.progress-container {
  padding: 24px;
  background: var(--progress-gradient);
  border-radius: 12px;
  color: white;
  margin-bottom: 20px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.progress-title {
  font-size: 18px;
  font-weight: 600;
}

.progress-count {
  font-size: 16px;
  opacity: 0.9;
}

.progress-bar {
  margin-bottom: 16px;
}

.progress-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.stat-item {
  font-size: 14px;
}

.stat-item.valid {
  color: #a5f3fc;
}

.stat-item.invalid {
  color: #fecaca;
}

.stat-item.time {
  color: #fef08a;
}

.stat-item.estimate {
  color: #c4b5fd;
}

.stat-item.strategy {
  color: #bbf7d0;
}

.progress-current {
  font-size: 12px;
  opacity: 0.9;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.current-label {
  white-space: nowrap;
}

.current-name {
  font-weight: 500;
  white-space: nowrap;
}

.current-name::after {
  content: '·';
  margin-left: 4px;
  opacity: 0.6;
}

.current-url {
  font-family: monospace;
  opacity: 0.8;
  word-break: break-all;
}

.progress-actions {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr);
  gap: 10px;
}

.cancel-btn,
.pause-btn,
.resume-btn {
  padding: 12px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  min-height: 44px;
}

.cancel-btn:hover,
.pause-btn:hover,
.resume-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
}

/* 移动端优化 */
@media (max-width: 575px) {
  .progress-container {
    padding: 16px;
  }

  .progress-title {
    font-size: 16px;
  }

  .progress-count {
    font-size: 14px;
  }

  .progress-stats {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .stat-item {
    font-size: 13px;
  }

  .progress-current {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .current-name,
  .current-url {
    white-space: normal;
  }

  .current-name::after {
    content: '';
  }

  .current-url {
    font-size: 11px;
  }

  .progress-actions {
    grid-template-columns: 1fr;
  }
}
</style>
