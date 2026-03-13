<template>
  <div class="search-validator">
    <div class="validator-header">
      <h3>🔍 搜索校验</h3>
      <p class="validator-desc">测试书源的搜索/发现功能是否可用</p>
    </div>

    <!-- 校验类型选择 -->
    <div class="validate-type">
      <span class="type-label">校验类型：</span>
      <button
        :class="['type-btn', { active: validateType === 'search' }]"
        @click="validateType = 'search'"
      >
        🔍 仅搜索
      </button>
      <button
        :class="['type-btn', { active: validateType === 'explore' }]"
        @click="validateType = 'explore'"
      >
        📚 仅发现
      </button>
      <button
        :class="['type-btn', { active: validateType === 'both' }]"
        @click="validateType = 'both'"
      >
        🔍📚 搜索+发现
      </button>
    </div>

    <!-- 搜索关键词（仅搜索模式显示） -->
    <div v-if="validateType === 'search' || validateType === 'both'" class="keyword-section">
      <span class="keyword-label">搜索关键词：</span>
      <div class="preset-keywords">
        <button
          v-for="kw in presetKeywords"
          :key="kw"
          :class="['keyword-btn', { active: keyword === kw }]"
          @click="keyword = kw"
        >
          {{ kw }}
        </button>
      </div>
      <div class="custom-keyword">
        <input
          v-model="customKeyword"
          type="text"
          placeholder="自定义关键词"
          class="keyword-input"
          @input="handleCustomInput"
        />
      </div>
    </div>

    <!-- 参数设置 -->
    <div class="settings-row">
      <ConcurrencySelector v-model="concurrency" />
      <TimeoutSelector v-model="timeout" />
    </div>

    <!-- 开始校验按钮 -->
    <button
      class="start-btn"
      :disabled="loading"
      @click="startValidation"
    >
      <span v-if="loading" class="loading-spinner"></span>
      {{ loading ? '校验中...' : '开始校验' }}
    </button>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import ConcurrencySelector from './ConcurrencySelector.vue'
import TimeoutSelector from './TimeoutSelector.vue'

const props = defineProps({
  loading: Boolean
})

const emit = defineEmits(['start-validation'])

// 预设关键词
const presetKeywords = ['玄幻', '重生', '穿越']

// 状态
const validateType = ref('search')  // 'search', 'explore', 'both'
const keyword = ref('玄幻')
const customKeyword = ref('')
const concurrency = ref(16)
const timeout = ref(30)

// 监听自定义关键词输入
function handleCustomInput() {
  if (customKeyword.value.trim()) {
    keyword.value = customKeyword.value.trim()
  }
}

// 开始校验
function startValidation() {
  console.log('=== SearchValidator.startValidation 被调用 ===')
  console.log('validateType:', validateType.value)
  console.log('keyword:', keyword.value)
  console.log('concurrency:', concurrency.value)
  console.log('timeout:', timeout.value)
  console.log('loading prop:', props.loading)

  emit('start-validation', {
    validateType: validateType.value,
    keyword: keyword.value,
    concurrency: concurrency.value,
    timeout: timeout.value
  })
  console.log('start-validation 事件已 emit')
}

// 暴露状态给父组件
defineExpose({
  validateType,
  keyword,
  concurrency,
  timeout
})
</script>

<style scoped>
.search-validator {
  background: var(--card-bg);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
}

.validator-header {
  margin-bottom: 16px;
}

.validator-header h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: var(--text-primary);
}

.validator-desc {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
}

.validate-type {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.type-label {
  font-size: 14px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.type-btn {
  padding: 8px 16px;
  border: 2px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.type-btn:hover {
  border-color: #409eff;
  color: var(--text-primary);
}

.type-btn.active {
  border-color: #409eff;
  background: var(--bg-tertiary);
  color: #409eff;
  font-weight: 500;
}

.keyword-section {
  margin-bottom: 16px;
}

.keyword-label {
  display: block;
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.preset-keywords {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.keyword-btn {
  padding: 6px 16px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border-radius: 16px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.keyword-btn:hover {
  border-color: #409eff;
  color: #409eff;
}

.keyword-btn.active {
  border-color: #409eff;
  background: #409eff;
  color: white;
}

.custom-keyword {
  margin-top: 8px;
}

.keyword-input {
  width: 100%;
  max-width: 200px;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 14px;
}

.keyword-input:focus {
  outline: none;
  border-color: #409eff;
}

.settings-row {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.start-btn {
  width: 100%;
  padding: 12px;
  background: #409eff;
  color: white;
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

.start-btn:hover:not(:disabled) {
  background: #66b1ff;
}

.start-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

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

@media (max-width: 575px) {
  .validate-type {
    flex-wrap: wrap;
  }

  .type-btn {
    flex: 1;
    min-width: 80px;
  }

  .settings-row {
    flex-direction: column;
    gap: 12px;
  }
}
</style>