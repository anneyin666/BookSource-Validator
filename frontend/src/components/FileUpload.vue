<template>
  <div class="file-upload">
    <!-- 拖拽区域 -->
    <div
      class="drop-zone"
      :class="{ 'is-dragging': isDragging, 'has-file': fileName }"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
      @click="triggerFileSelect"
    >
      <div class="drop-icon">📁</div>

      <template v-if="fileName">
        <p class="file-name">{{ fileName }} ✓</p>
        <p class="file-hint">点击或拖拽重新上传</p>
      </template>

      <template v-else>
        <p class="drop-text">拖拽文件到此处，或点击上传</p>
        <p class="drop-hint">支持 .json、.txt 格式文件，最大 10MB</p>
      </template>

      <input
        ref="fileInput"
        type="file"
        accept=".json,.txt,application/json,text/plain"
        hidden
        @change="handleFileChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  loading: Boolean,
  fileName: String
})

const emit = defineEmits(['upload'])

const fileInput = ref(null)
const isDragging = ref(false)

function triggerFileSelect() {
  if (props.loading) return
  fileInput.value?.click()
}

function handleFileChange(event) {
  const target = event.target
  const file = target.files?.[0]
  if (file) {
    validateAndUpload(file)
  }
}

function handleDragOver() {
  isDragging.value = true
}

function handleDragLeave() {
  isDragging.value = false
}

function handleDrop(event) {
  isDragging.value = false

  const file = event.dataTransfer?.files[0]
  if (file) {
    validateAndUpload(file)
  }
}

function validateAndUpload(file) {
  // 检查文件类型
  const lowerName = file.name.toLowerCase()
  if (!lowerName.endsWith('.json') && !lowerName.endsWith('.txt') && file.type !== 'application/json') {
    alert('请上传 JSON 或 TXT 格式文件')
    return
  }

  // 检查文件大小 (10MB)
  if (file.size > 10 * 1024 * 1024) {
    alert('文件大小不能超过 10MB')
    return
  }

  emit('upload', file)
}
</script>

<style scoped>
.file-upload {
  width: 100%;
}

.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  background: var(--bg-secondary);
  cursor: pointer;
  transition: all 0.3s ease;
  min-height: 140px;
}

.drop-zone:hover {
  border-color: #409eff;
  background: var(--bg-tertiary);
}

.drop-zone.is-dragging {
  border-color: #409eff;
  background: var(--bg-tertiary);
  transform: scale(1.02);
}

.drop-zone.has-file {
  border-color: #67c23a;
  background: var(--bg-tertiary);
}

.drop-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.drop-text {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.drop-hint,
.file-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.file-name {
  font-size: 16px;
  color: #67c23a;
  font-weight: 500;
  margin-bottom: 8px;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .drop-zone {
    padding: 32px 16px;
    min-height: 120px;
  }

  .drop-icon {
    font-size: 40px;
    margin-bottom: 12px;
  }

  .drop-text,
  .file-name {
    font-size: 15px;
  }

  .drop-hint,
  .file-hint {
    font-size: 11px;
  }
}

@media (max-width: 575px) {
  .drop-zone {
    padding: 24px 12px;
    min-height: 100px;
  }

  .drop-icon {
    font-size: 36px;
    margin-bottom: 8px;
  }

  .drop-text,
  .file-name {
    font-size: 14px;
  }
}

/* 触摸设备优化 */
@media (hover: none) and (pointer: coarse) {
  .drop-zone {
    min-height: 120px;
    padding: 24px 16px;
  }

  .drop-zone:active {
    transform: scale(0.98);
    opacity: 0.9;
  }

  .drop-icon {
    font-size: 40px;
  }

  .drop-text,
  .file-name {
    font-size: 15px;
  }
}
</style>