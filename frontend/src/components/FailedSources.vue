<template>
  <div class="failed-sources" v-if="hasFailedSources">
    <h3 class="section-title">❌ 失败书源分析</h3>

    <!-- 可修复错误 -->
    <div v-if="fixableSources.length" class="error-section fixable">
      <div class="section-header" @click="toggleSection('fixable')">
        <span class="section-icon">🔄</span>
        <span class="section-name">可修复</span>
        <span class="section-count">({{ fixableSources.length }})</span>
        <span class="expand-icon">{{ expandedSections.fixable ? '▼' : '▶' }}</span>
      </div>
      <p class="section-hint">这些书源可能因网络问题暂时失效，可稍后重试</p>
      <div class="source-list" v-show="expandedSections.fixable">
        <div v-for="source in fixableSources.slice(0, displayLimit.fixable)" :key="source.url" class="source-item">
          <span class="source-name">{{ truncateText(source.name, 25) }}</span>
          <span class="source-reason">{{ source.reason }}</span>
        </div>
        <button
          v-if="fixableSources.length > displayLimit.fixable"
          class="show-more-btn"
          @click="displayLimit.fixable = fixableSources.length"
        >
          显示全部 {{ fixableSources.length }} 条
        </button>
      </div>
    </div>

    <!-- 不可修复错误 -->
    <div v-if="unfixableSources.length" class="error-section unfixable">
      <div class="section-header" @click="toggleSection('unfixable')">
        <span class="section-icon">❌</span>
        <span class="section-name">不可修复</span>
        <span class="section-count">({{ unfixableSources.length }})</span>
        <span class="expand-icon">{{ expandedSections.unfixable ? '▼' : '▶' }}</span>
      </div>
      <p class="section-hint">这些书源规则有问题或使用了不支持的加密</p>
      <div class="source-list" v-show="expandedSections.unfixable">
        <div v-for="source in unfixableSources.slice(0, displayLimit.unfixable)" :key="source.url" class="source-item">
          <span class="source-name">{{ truncateText(source.name, 25) }}</span>
          <span class="source-reason">{{ source.reason }}</span>
        </div>
        <button
          v-if="unfixableSources.length > displayLimit.unfixable"
          class="show-more-btn"
          @click="displayLimit.unfixable = unfixableSources.length"
        >
          显示全部 {{ unfixableSources.length }} 条
        </button>
      </div>
    </div>

    <!-- 需检查错误 -->
    <div v-if="checkableSources.length" class="error-section checkable">
      <div class="section-header" @click="toggleSection('checkable')">
        <span class="section-icon">⚠️</span>
        <span class="section-name">需检查</span>
        <span class="section-count">({{ checkableSources.length }})</span>
        <span class="expand-icon">{{ expandedSections.checkable ? '▼' : '▶' }}</span>
      </div>
      <p class="section-hint">这些书源可能已下线或内容有变化</p>
      <div class="source-list" v-show="expandedSections.checkable">
        <div v-for="source in checkableSources.slice(0, displayLimit.checkable)" :key="source.url" class="source-item">
          <span class="source-name">{{ truncateText(source.name, 25) }}</span>
          <span class="source-reason">{{ source.reason }}</span>
        </div>
        <button
          v-if="checkableSources.length > displayLimit.checkable"
          class="show-more-btn"
          @click="displayLimit.checkable = checkableSources.length"
        >
          显示全部 {{ checkableSources.length }} 条
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, reactive } from 'vue'

const props = defineProps({
  failedCategories: {
    type: Object,
    default: () => ({})
  }
})

// 展开状态
const expandedSections = reactive({
  fixable: true,
  unfixable: true,
  checkable: true
})

// 显示数量限制
const displayLimit = reactive({
  fixable: 10,
  unfixable: 10,
  checkable: 10
})

// 分类数据
const fixableSources = computed(() => props.failedCategories?.fixable || [])
const unfixableSources = computed(() => props.failedCategories?.unfixable || [])
const checkableSources = computed(() => props.failedCategories?.checkable || [])

const hasFailedSources = computed(() =>
  fixableSources.value.length > 0 ||
  unfixableSources.value.length > 0 ||
  checkableSources.value.length > 0
)

// 切换展开状态
function toggleSection(section) {
  expandedSections[section] = !expandedSections[section]
}

// 截断文本
function truncateText(text, maxLen) {
  if (!text) return ''
  if (text.length > maxLen) {
    return text.substring(0, maxLen) + '...'
  }
  return text
}
</script>

<style scoped>
.failed-sources {
  margin-top: 20px;
}

.section-title {
  font-size: 16px;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.error-section {
  margin-bottom: 16px;
  border-radius: 8px;
  overflow: hidden;
}

.error-section.fixable {
  background: rgba(251, 146, 60, 0.1);
  border: 1px solid rgba(251, 146, 60, 0.3);
}

.error-section.unfixable {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.error-section.checkable {
  background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.3);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
}

.section-header:hover {
  background: rgba(0, 0, 0, 0.05);
}

.error-section.unfixable .section-header:hover {
  background: rgba(239, 68, 68, 0.1);
}

.section-icon {
  font-size: 18px;
}

.section-name {
  font-weight: 600;
  color: var(--text-primary);
}

.section-count {
  color: var(--text-secondary);
  font-size: 14px;
}

.expand-icon {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-secondary);
}

.section-hint {
  margin: 0;
  padding: 0 16px 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.source-list {
  padding: 0 16px 16px;
}

.source-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 6px;
  margin-bottom: 8px;
  gap: 12px;
}

[data-theme="dark"] .source-item {
  background: rgba(0, 0, 0, 0.2);
}

.source-name {
  font-size: 14px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.source-reason {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.show-more-btn {
  width: 100%;
  padding: 8px;
  background: transparent;
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.show-more-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: var(--text-primary);
}

[data-theme="dark"] .show-more-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

/* 移动端优化 */
@media (max-width: 575px) {
  .source-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .source-reason {
    font-size: 11px;
  }
}
</style>