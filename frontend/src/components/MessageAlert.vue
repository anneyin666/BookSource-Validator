<template>
  <div class="message-alert">
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      closable
      @close="$emit('close')"
    />
    <el-alert
      v-if="success"
      :title="success"
      type="success"
      show-icon
      closable
      @close="$emit('close')"
    />
    <el-alert
      v-if="warning"
      :title="warning"
      type="warning"
      show-icon
      closable
      @close="$emit('close')"
    />
  </div>
</template>

<script setup>
defineProps({
  error: String,
  success: String,
  warning: String
})

defineEmits(['close'])
</script>

<style scoped>
.message-alert {
  margin-bottom: 24px;
}

.message-alert .el-alert + .el-alert {
  margin-top: 12px;
}
</style>