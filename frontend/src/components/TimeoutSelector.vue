<template>
  <div class="timeout-selector">
    <label v-if="showLabel" class="timeout-label">
      <span class="label-full">⏱️ 超时时间：</span>
      <span class="label-short">超时：</span>
    </label>
    <el-input-number
      v-model="selectedTimeout"
      :min="5"
      :max="120"
      :step="5"
      controls-position="right"
      class="timeout-select"
    />
    <span v-if="showUnit" class="timeout-unit">秒</span>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Number,
    default: 30
  },
  showLabel: {
    type: Boolean,
    default: true
  },
  showUnit: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:modelValue'])

const selectedTimeout = ref(props.modelValue)

watch(() => props.modelValue, (val) => {
  selectedTimeout.value = val
})

watch(selectedTimeout, (val) => {
  emit('update:modelValue', val)
})
</script>

<style scoped>
.timeout-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.timeout-label {
  font-size: 14px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.label-short {
  display: none;
}

.timeout-select {
  width: 112px;
  flex: 0 0 auto;
}

.timeout-unit {
  color: var(--text-muted);
  flex: 0 0 auto;
  font-size: 13px;
}

@media (max-width: 575px) {
  .timeout-selector {
    justify-content: center;
    gap: 6px;
  }

  .timeout-label {
    font-size: 13px;
  }

  .label-full {
    display: none;
  }

  .label-short {
    display: inline;
  }

  .timeout-select {
    width: 104px;
  }
}
</style>
