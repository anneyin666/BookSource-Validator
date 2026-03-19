<template>
  <div class="url-input">
    <div class="input-label">在线链接:</div>

    <div class="input-group">
      <el-input
        v-model="url"
        placeholder="请输入在线书源链接..."
        :disabled="loading"
        clearable
        @keyup.enter="handleFetch"
      >
        <template #prefix>
          <span>🔗</span>
        </template>
      </el-input>

      <el-button
        type="info"
        :disabled="loading"
        @click="handlePaste"
        title="从剪贴板粘贴"
      >
        📋
      </el-button>

      <el-button
        type="primary"
        :loading="loading"
        @click="handleFetch"
      >
        获取
      </el-button>
    </div>

    <p class="input-hint">支持直接数组或嵌套格式（如 sources、data 字段）| 💡 按 Ctrl+V 可直接粘贴解析</p>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  loading: Boolean,
  url: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['fetch', 'paste'])

const url = ref(props.url || '')

// 同步外部 URL
watch(() => props.url, (val) => {
  url.value = val || ''
})

function handleFetch() {
  const trimmedUrl = url.value.trim()

  if (!trimmedUrl) {
    return
  }

  // 验证 URL 格式
  if (!isValidUrl(trimmedUrl)) {
    alert('请输入有效的 URL 地址')
    return
  }

  emit('fetch', trimmedUrl)
}

async function handlePaste() {
  try {
    const text = await navigator.clipboard.readText()
    if (text && text.trim().startsWith('http')) {
      url.value = text.trim()
      emit('paste')
    } else {
      alert('剪贴板内容不是有效的链接')
    }
  } catch (err) {
    alert('无法读取剪贴板，请手动粘贴')
  }
}

function isValidUrl(str) {
  try {
    const urlObj = new URL(str)
    return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
  } catch {
    return false
  }
}
</script>

<style scoped>
.url-input {
  width: 100%;
}

.input-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.input-group {
  display: flex;
  gap: 12px;
}

.input-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 8px;
}
</style>
