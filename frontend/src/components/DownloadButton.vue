<template>
  <div class="download-button">
    <div class="download-actions">
      <el-button
        type="success"
        size="large"
        :disabled="!enabled"
        @click="$emit('download')"
      >
        <span class="btn-icon">⬇️</span>
        <span>下载去重后的 JSON</span>
        <span v-if="count > 0" class="btn-count">({{ count }}条)</span>
      </el-button>

      <el-button
        type="primary"
        plain
        size="large"
        :disabled="!enabled"
        :loading="exportingApp"
        @click="$emit('export-app')"
      >
        <span class="btn-icon">📱</span>
        <span>{{ appReady ? '导出到阅读 App' : '准备导出到阅读 App' }}</span>
      </el-button>
    </div>

    <p class="download-hint">手机浏览器可一键唤起阅读 App；桌面端仍可直接下载 JSON。</p>
  </div>
</template>

<script setup>
defineProps({
  enabled: Boolean,
  count: {
    type: Number,
    default: 0
  },
  exportingApp: {
    type: Boolean,
    default: false
  },
  appReady: {
    type: Boolean,
    default: false
  }
})

defineEmits(['download', 'export-app'])
</script>

<style scoped>
.download-button {
  margin-top: 24px;
  text-align: center;
}

.download-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.download-actions .el-button {
  padding: 12px 32px;
  height: auto;
  white-space: normal;
}

.btn-icon {
  margin-right: 8px;
}

.btn-count {
  margin-left: 8px;
  opacity: 0.8;
}

.download-hint {
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-muted);
}

@media (max-width: 575px) {
  .download-actions {
    flex-direction: column;
  }

  .download-actions .el-button {
    width: 100%;
    padding: 12px 16px;
  }
}
</style>
