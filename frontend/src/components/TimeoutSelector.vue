<template>
  <div class="timeout-selector">
    <label class="timeout-label">⏱️ 超时时间：</label>
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
  color: #606266;
  white-space: nowrap;
}

.timeout-select {
  width: 100px;
}
</style>