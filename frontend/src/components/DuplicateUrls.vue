<template>
  <div class="duplicate-urls" v-if="duplicateUrls && duplicateUrls.length > 0">
    <div class="duplicate-header" @click="expanded = !expanded">
      <span class="header-icon">{{ expanded ? '▼' : '▶' }}</span>
      <span class="header-text">发现 {{ duplicateUrls.length }} 个重复URL</span>
      <span class="header-hint">点击{{ expanded ? '收起' : '展开' }}</span>
    </div>
    <div class="duplicate-list" v-show="expanded">
      <div class="duplicate-item" v-for="(item, index) in duplicateUrls" :key="index">
        <span class="duplicate-count">{{ item.count }}次</span>
        <span class="duplicate-url" :title="item.url">{{ truncateUrl(item.url) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  duplicateUrls: {
    type: Array,
    default: () => []
  }
})

const expanded = ref(false)

function truncateUrl(url) {
  if (!url) return ''
  if (url.length <= 60) return url
  return url.substring(0, 60) + '...'
}
</script>

<style scoped>
.duplicate-urls {
  margin-top: 16px;
  background: #fff8e6;
  border: 1px solid #ffc107;
  border-radius: 8px;
  overflow: hidden;
}

.duplicate-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  background: #fff3cd;
  transition: background 0.2s;
}

.duplicate-header:hover {
  background: #ffe69c;
}

.header-icon {
  margin-right: 8px;
  font-size: 12px;
  color: #856404;
}

.header-text {
  font-weight: 600;
  color: #856404;
  flex: 1;
}

.header-hint {
  font-size: 12px;
  color: #997a00;
}

.duplicate-list {
  max-height: 300px;
  overflow-y: auto;
  border-top: 1px solid #ffc107;
}

.duplicate-item {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid #f0e6c8;
}

.duplicate-item:last-child {
  border-bottom: none;
}

.duplicate-count {
  background: #ff9800;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  margin-right: 12px;
  min-width: 40px;
  text-align: center;
}

.duplicate-url {
  font-family: monospace;
  font-size: 13px;
  color: #666;
  word-break: break-all;
}
</style>