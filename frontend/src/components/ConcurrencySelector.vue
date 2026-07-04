<template>
  <div class="concurrency-selector">
    <label v-if="showLabel" class="selector-label">
      <span class="label-full">并发数：</span>
      <span class="label-short">并发：</span>
    </label>
    <el-input-number
      v-model="selectedConcurrency"
      :min="1"
      :max="64"
      :step="1"
      size="default"
      controls-position="right"
      class="concurrency-select"
    />
    <el-tooltip content="支持 1-64。智能策略会在错误率高或响应慢时自动降并发" placement="top">
      <el-icon class="help-icon"><QuestionFilled /></el-icon>
    </el-tooltip>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { QuestionFilled } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: {
    type: Number,
    default: 16
  },
  showLabel: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:modelValue'])

const selectedConcurrency = ref(props.modelValue)

watch(selectedConcurrency, (newVal) => {
  emit('update:modelValue', newVal)
})

watch(() => props.modelValue, (newVal) => {
  selectedConcurrency.value = newVal
})
</script>

<style scoped>
.concurrency-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.selector-label {
  font-size: 14px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.label-short {
  display: none;
}

.help-icon {
  color: #909399;
  cursor: help;
  flex: 0 0 auto;
  font-size: 16px;
}

.concurrency-select {
  width: 112px;
  flex: 0 0 auto;
}

@media (max-width: 575px) {
  .concurrency-selector {
    justify-content: center;
    gap: 6px;
  }

  .selector-label {
    font-size: 13px;
  }

  .label-full {
    display: none;
  }

  .label-short {
    display: inline;
  }

  .help-icon {
    display: none;
  }

  .concurrency-select {
    width: 104px;
  }
}
</style>
