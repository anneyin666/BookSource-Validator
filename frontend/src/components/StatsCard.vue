<template>
  <div class="stats-card" :class="`theme-${theme}`">
    <div class="stats-value">{{ displayValue }}</div>
    <div class="stats-label">{{ label }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: [Number, String],
  label: String,
  theme: {
    type: String,
    default: 'primary'
  }
})

const displayValue = computed(() => {
  if (typeof props.value === 'number') {
    return props.value.toLocaleString()
  }
  return props.value
})
</script>

<style scoped>
.stats-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 32px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  min-width: 120px;
}

.stats-card.theme-primary .stats-value {
  color: #409eff;
}

.stats-card.theme-success .stats-value {
  color: #67c23a;
}

.stats-card.theme-warning .stats-value {
  color: #e6a23c;
}

.stats-value {
  font-size: 36px;
  font-weight: 600;
  line-height: 1;
  margin-bottom: 8px;
}

.stats-label {
  font-size: 14px;
  color: #909399;
}
</style>