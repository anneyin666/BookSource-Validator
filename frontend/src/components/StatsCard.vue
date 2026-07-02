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
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 2px 12px var(--shadow-color);
  min-width: 120px;
  transition: background-color 0.2s, border-color 0.2s, box-shadow 0.2s;
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
  color: var(--text-muted);
}

@media (max-width: 576px) {
  .stats-card {
    min-width: 0;
    width: 100%;
    padding: 18px 10px;
  }

  .stats-card.stat-card-main .stats-value {
    font-size: 32px;
  }

  .stats-card.stat-card-secondary {
    padding: 16px 6px;
  }

  .stats-card.stat-card-secondary .stats-value {
    font-size: 28px;
  }

  .stats-label {
    font-size: 13px;
    white-space: nowrap;
  }
}
</style>
