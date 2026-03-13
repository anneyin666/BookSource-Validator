<template>
  <div class="concurrency-selector">
    <label class="selector-label">并发数：</label>
    <el-select v-model="selectedConcurrency" size="default" style="width: 100px">
      <el-option
        v-for="option in options"
        :key="option.value"
        :label="option.label"
        :value="option.value"
      />
    </el-select>
    <el-tooltip content="并发数越高，校验速度越快，但可能增加服务器压力" placement="top">
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
  }
})

const emit = defineEmits(['update:modelValue'])

const options = [
  { value: 1, label: '1线程' },
  { value: 4, label: '4线程' },
  { value: 8, label: '8线程' },
  { value: 16, label: '16线程' },
  { value: 32, label: '32线程' }
]

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
}

.selector-label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

.help-icon {
  color: #909399;
  cursor: help;
  font-size: 16px;
}
</style>