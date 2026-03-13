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
    </div>

    <div class="progress-current" v-if="currentUrl || currentName">
      <span class="current-label">当前:</span>
      <span class="current-name" v-if="currentName">{{ truncateText(currentName, 20) }}</span>
      <span class="current-url" v-if="currentUrl">{{ truncateUrl(currentUrl) }}</span>
    </div>

    <button class="cancel-btn" @click="$emit('cancel')">
      ⏹️ 取消校验
    </button>
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
  }
})

defineEmits(['cancel'])

const percentage = computed(() => {
  if (props.total === 0) return 0
  return Math.round((props.processed / props.total) * 100)
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
    return `${seconds}秒`
  }
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
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

.progress-current {
  font-size: 12px;
  opacity: 0.9;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
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
}

.cancel-btn {
  width: 100%;
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

.cancel-btn:hover {
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
    gap: 12px;
  }

  .stat-item {
    font-size: 13px;
  }

  .progress-current {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .current-name::after {
    content: '';
  }

  .current-url {
    font-size: 11px;
  }
}
</style>