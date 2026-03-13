<template>
  <div class="filter-options">
    <span class="filter-label">过滤类型：</span>
    <el-checkbox-group v-model="selectedTypes" size="small">
      <el-checkbox label="official">正版书籍</el-checkbox>
      <el-checkbox label="audio">听书源</el-checkbox>
      <el-checkbox label="comic">漫画源</el-checkbox>
      <el-checkbox label="video">影视源</el-checkbox>
    </el-checkbox-group>
    <span class="filter-hint">（勾选将移除该类型书源）</span>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const selectedTypes = ref([])

const emit = defineEmits(['update:modelValue'])

watch(selectedTypes, (val) => {
  emit('update:modelValue', val)
}, { immediate: true })
</script>

<style scoped>
.filter-options {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--card-bg);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.filter-label {
  font-weight: 500;
  color: var(--text-secondary);
  white-space: nowrap;
}

.filter-hint {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}

@media (max-width: 768px) {
  .filter-options {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>