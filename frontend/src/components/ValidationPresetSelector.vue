<template>
  <div class="preset-selector">
    <span class="preset-label">策略：</span>
    <button
      v-for="preset in presets"
      :key="preset.value"
      :class="['preset-btn', { active: modelValue === preset.value }]"
      type="button"
      @click="selectPreset(preset)"
    >
      <span class="preset-name">{{ preset.label }}</span>
      <span class="preset-hint">{{ preset.hint }}</span>
    </button>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    default: 'balanced'
  }
})

const emit = defineEmits(['update:modelValue', 'apply'])

const presets = [
  { value: 'fast', label: '快速', hint: '32 / 15秒', concurrency: 32, timeout: 15 },
  { value: 'balanced', label: '均衡', hint: '16 / 30秒', concurrency: 16, timeout: 30 },
  { value: 'stable', label: '稳定', hint: '8 / 45秒', concurrency: 8, timeout: 45 },
  { value: 'custom', label: '自定义', hint: '手动参数' }
]

function selectPreset(preset) {
  emit('update:modelValue', preset.value)
  emit('apply', preset)
}
</script>

<style scoped>
.preset-selector {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
  width: 100%;
}

.preset-label {
  color: var(--text-secondary);
  font-size: 14px;
  white-space: nowrap;
}

.preset-btn {
  min-width: 82px;
  padding: 7px 10px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--card-bg);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.preset-btn:hover {
  border-color: #409eff;
  color: #409eff;
}

.preset-btn.active {
  border-color: #409eff;
  background: var(--bg-tertiary);
  color: #409eff;
}

.preset-name {
  display: block;
  font-size: 13px;
  font-weight: 600;
}

.preset-hint {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  opacity: 0.8;
}

@media (max-width: 575px) {
  .preset-selector {
    grid-column: 1 / -1;
    gap: 6px;
  }

  .preset-label {
    width: 100%;
    text-align: center;
  }

  .preset-btn {
    flex: 1 1 calc(50% - 6px);
    min-width: 0;
  }
}
</style>
