<template>
  <div class="action-buttons">
    <el-button
      type="primary"
      size="large"
      :loading="loading"
      :disabled="validating"
      @click="$emit('dedup')"
    >
      <span class="btn-icon">🔍</span>
      <span>只查重复</span>
      <span class="btn-hint">快速去重</span>
    </el-button>

    <el-button
      type="success"
      size="large"
      :loading="validating"
      :disabled="loading"
      @click="$emit('full-validate')"
    >
      <span class="btn-icon">✅</span>
      <span>全部校验</span>
      <span class="btn-hint">去重+深度校验</span>
    </el-button>
  </div>
</template>

<script setup>
defineProps({
  loading: Boolean,
  validating: Boolean
})

defineEmits(['dedup', 'full-validate'])
</script>

<style scoped>
.action-buttons {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin: 24px 0;
}

.action-buttons .el-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 32px;
  height: auto;
}

.btn-icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.btn-hint {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  margin-top: 4px;
}

@media (max-width: 576px) {
  .action-buttons {
    flex-direction: column;
    align-items: center;
  }
}
</style>