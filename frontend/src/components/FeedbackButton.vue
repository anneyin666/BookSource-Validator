<template>
  <div class="feedback-entry">
    <button class="feedback-button" type="button" @click="openDialog">
      反馈
    </button>

    <div v-if="visible" class="feedback-backdrop" @click.self="closeDialog">
      <section class="feedback-dialog" role="dialog" aria-modal="true" aria-labelledby="feedback-title">
        <header class="feedback-header">
          <h2 id="feedback-title">问题反馈</h2>
          <button class="feedback-close" type="button" @click="closeDialog" aria-label="关闭">×</button>
        </header>

        <textarea
          v-model.trim="message"
          class="feedback-textarea"
          maxlength="2000"
          placeholder="请描述你遇到的问题、操作步骤或希望优化的地方"
        />

        <input
          v-model.trim="contact"
          class="feedback-contact"
          maxlength="200"
          placeholder="联系方式，可不填"
        />

        <p v-if="statusMessage" class="feedback-status" :class="{ error: hasError }">
          {{ statusMessage }}
        </p>

        <footer class="feedback-actions">
          <button class="feedback-secondary" type="button" @click="closeDialog">取消</button>
          <button class="feedback-primary" type="button" :disabled="submitting || !message" @click="handleSubmit">
            {{ submitting ? '提交中...' : '提交反馈' }}
          </button>
        </footer>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { submitFeedback } from '../api/sources.js'
import { useToast } from '../composables/useToast.js'

const { showSuccess, showError } = useToast()

const visible = ref(false)
const message = ref('')
const contact = ref('')
const submitting = ref(false)
const statusMessage = ref('')
const hasError = ref(false)

function openDialog() {
  visible.value = true
  statusMessage.value = ''
  hasError.value = false
}

function closeDialog() {
  if (submitting.value) return
  visible.value = false
}

async function handleSubmit() {
  if (!message.value || submitting.value) return

  submitting.value = true
  statusMessage.value = ''
  hasError.value = false

  try {
    const result = await submitFeedback({
      message: message.value,
      contact: contact.value,
      page_url: window.location.href,
      user_agent: window.navigator.userAgent,
      viewport: `${window.innerWidth}x${window.innerHeight}`,
      theme: document.documentElement.getAttribute('data-theme') || 'light'
    })

    if (result.code !== 200) {
      throw new Error(result.message || '提交失败')
    }

    message.value = ''
    contact.value = ''
    visible.value = false
    showSuccess('反馈已提交')
  } catch (err) {
    hasError.value = true
    statusMessage.value = err.message || '提交失败，请稍后重试'
    showError(statusMessage.value)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.feedback-button {
  position: fixed;
  top: 20px;
  left: 20px;
  z-index: 1000;
  height: 36px;
  padding: 0 14px;
  border: 1px solid var(--border-color);
  border-radius: 18px;
  background: var(--card-bg);
  color: var(--text-primary);
  box-shadow: 0 2px 8px var(--shadow-color);
  cursor: pointer;
  font-size: 13px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.feedback-button:hover {
  border-color: #409eff;
  box-shadow: 0 4px 12px var(--shadow-color);
}

.feedback-backdrop {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.45);
}

.feedback-dialog {
  width: min(480px, 100%);
  padding: 18px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--card-bg);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.24);
}

.feedback-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.feedback-header h2 {
  font-size: 18px;
  color: var(--text-primary);
}

.feedback-close {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 24px;
  line-height: 1;
}

.feedback-textarea,
.feedback-contact {
  width: 100%;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  outline: none;
}

.feedback-textarea {
  min-height: 140px;
  padding: 12px;
  resize: vertical;
  line-height: 1.6;
}

.feedback-contact {
  margin-top: 10px;
  padding: 10px 12px;
}

.feedback-textarea:focus,
.feedback-contact:focus {
  border-color: #409eff;
}

.feedback-status {
  margin-top: 10px;
  color: #67c23a;
  font-size: 13px;
}

.feedback-status.error {
  color: #f56c6c;
}

.feedback-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}

.feedback-secondary,
.feedback-primary {
  min-height: 38px;
  padding: 0 16px;
  border-radius: 6px;
  cursor: pointer;
}

.feedback-secondary {
  border: 1px solid var(--border-color);
  background: var(--card-bg);
  color: var(--text-secondary);
}

.feedback-primary {
  border: 1px solid #409eff;
  background: #409eff;
  color: white;
}

.feedback-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .feedback-button {
    top: 12px;
    left: 12px;
    height: 34px;
    padding: 0 12px;
  }
}
</style>
