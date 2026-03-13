<template>
  <div class="download-button">
    <el-button
      type="success"
      size="large"
      :disabled="!enabled"
      @click="$emit('download')"
    >
      <span class="btn-icon">⬇️</span>
      <span>下载去重后的JSON</span>
      <span v-if="count > 0" class="btn-count">({{ count }}条)</span>
    </el-button>
  </div>
</template>

<script setup>
defineProps({
  enabled: Boolean,
  count: {
    type: Number,
    default: 0
  }
})

defineEmits(['download'])
</script>

<style scoped>
.download-button {
  margin-top: 24px;
  text-align: center;
}

.download-button .el-button {
  padding: 12px 32px;
  height: auto;
}

.btn-icon {
  margin-right: 8px;
}

.btn-count {
  margin-left: 8px;
  opacity: 0.8;
}
</style>