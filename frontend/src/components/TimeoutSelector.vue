<template>
  <div class="timeout-selector">
    <label class="timeout-label">
      <span class="label-full">⏱️ 超时时间：</span>
      <span class="label-short">超时：</span>
    </label>
    <el-select v-model="selectedTimeout" class="timeout-select" @change="handleChange">
      <el-option
        v-for="t in timeoutOptions"
        :key="t"
        :label="`${t} 秒`"
        :value="t"
      />
    </el-select>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Number,
    default: 30
  }
})

const emit = defineEmits(['update:modelValue'])

const timeoutOptions = [15, 30, 45, 60]
const selectedTimeout = ref(props.modelValue)

watch(() => props.modelValue, (val) => {
  selectedTimeout.value = val
})

function handleChange(val) {
  emit('update:modelValue', val)
}
</script>

<style scoped>
.timeout-selector {
  display: flex;
  align-items: center;
  gap: 8px;
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
  width: 100px;
}

@media (max-width: 575px) {
  .timeout-selector {
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
    width: 96px;
  }
}
</style>
