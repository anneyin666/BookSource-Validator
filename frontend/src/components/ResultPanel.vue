<template>
  <section class="stats-section">
    <h2 class="section-title">📊 统计结果</h2>
    <StatsCardGroup :stats="stats" />

    <!-- 规则类型统计（搜索校验模式） -->
    <div v-if="stats.ruleTypeStats && processMode === 'search'" class="rule-type-stats">
      <h3 class="rule-type-title">📋 规则类型分布</h3>
      <div class="rule-type-cards">
        <div class="rule-type-card search-only">
          <div class="rule-type-label">🔍 仅搜索</div>
          <div class="rule-type-numbers">
            <span class="valid">{{ stats.ruleTypeStats.searchOnly.valid }} 有效</span>
            <span class="invalid">{{ stats.ruleTypeStats.searchOnly.invalid }} 失效</span>
          </div>
          <div class="rule-type-total">共 {{ stats.ruleTypeStats.searchOnly.total }} 条</div>
        </div>
        <div class="rule-type-card explore-only">
          <div class="rule-type-label">📖 仅发现</div>
          <div class="rule-type-numbers">
            <span class="valid">{{ stats.ruleTypeStats.exploreOnly.valid }} 有效</span>
            <span class="invalid">{{ stats.ruleTypeStats.exploreOnly.invalid }} 失效</span>
          </div>
          <div class="rule-type-total">共 {{ stats.ruleTypeStats.exploreOnly.total }} 条</div>
        </div>
        <div class="rule-type-card both">
          <div class="rule-type-label">🔍📖 搜索+发现</div>
          <div class="rule-type-numbers">
            <span class="valid">{{ stats.ruleTypeStats.both.valid }} 有效</span>
            <span class="invalid">{{ stats.ruleTypeStats.both.invalid }} 失效</span>
          </div>
          <div class="rule-type-total">共 {{ stats.ruleTypeStats.both.total }} 条</div>
        </div>
        <div class="rule-type-card none" v-if="stats.ruleTypeStats.none.total > 0">
          <div class="rule-type-label">❌ 无规则</div>
          <div class="rule-type-numbers">
            <span class="invalid">{{ stats.ruleTypeStats.none.invalid }} 失效</span>
          </div>
          <div class="rule-type-total">共 {{ stats.ruleTypeStats.none.total }} 条</div>
        </div>
      </div>
    </div>

    <!-- 失败书源分析（分类展示） -->
    <FailedSources
      v-if="hasFailedCategories"
      :failed-categories="sourceData.failedCategories"
    />

    <!-- 失败书源分组（详细列表） -->
    <div v-if="hasFailedGroups" class="failed-groups">
      <h3 class="failed-title">📋 失败详情（按原因分组）</h3>
      <div class="failed-list">
        <div
          v-for="group in sourceData.failedGroups"
          :key="group.reason || 'unknown'"
          class="failed-item"
        >
          <div class="failed-header" @click="$emit('toggle-group', group.reason)">
            <span class="failed-reason">{{ group.reason || '未知错误' }}</span>
            <span class="failed-count">{{ group.count }} 条</span>
            <span class="failed-toggle">{{ expandedGroups[group.reason] ? '▼' : '▶' }}</span>
          </div>
          <div v-if="expandedGroups[group.reason]" class="failed-sources">
            <div
              v-for="source in group.sources"
              :key="source.bookSourceUrl"
              class="failed-source-item"
            >
              <span class="source-name">{{ source.bookSourceName || '未命名' }}</span>
              <span class="source-url">{{ source.bookSourceUrl }}</span>
            </div>
          </div>
        </div>
      </div>
      <!-- 导出失败书源按钮 -->
      <div class="failed-actions">
        <button class="retry-failed-btn" @click="$emit('retry-failed', false)">
          🔁 重试全部失败
        </button>
        <button class="retry-network-btn" @click="$emit('retry-failed', true)">
          🌐 仅重试网络/超时
        </button>
        <button class="export-failed-btn" @click="$emit('export-failed')">
          📥 导出失败书源
        </button>
      </div>
    </div>

    <DownloadButton
      :enabled="hasValidSources"
      :count="sourceData.validCount || 0"
      :exporting-app="legadoExport.loading"
      :app-ready="legadoExport.ready"
      @download="$emit('download')"
      @export-app="$emit('export-app')"
    />

    <div
      v-if="hasValidSources && (legadoExport.loading || legadoExport.downloadUrl)"
      class="mobile-export-panel"
    >
      <p class="mobile-export-title">导出到阅读 App</p>
      <p class="mobile-export-hint">
        手机浏览器可直接唤起阅读导入当前有效书源；如果没有自动跳转，可改用下面的临时 JSON 链接。
      </p>
      <p v-if="legadoExport.loading" class="mobile-export-status">正在准备临时导出链接...</p>
      <div v-else class="mobile-export-links">
        <a
          class="mobile-export-link"
          :href="legadoExport.downloadUrl"
          target="_blank"
          rel="noreferrer"
        >
          打开临时 JSON 链接
        </a>
        <span class="mobile-export-expire">{{ legadoExportExpireText }}</span>
      </div>
    </div>

    <!-- 重新处理按钮 -->
    <button class="restart-btn" @click="$emit('restart')">
      🔄 重新处理
    </button>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import StatsCardGroup from './StatsCardGroup.vue'
import FailedSources from './FailedSources.vue'
import DownloadButton from './DownloadButton.vue'

const props = defineProps({
  sourceData: { type: Object, required: true },
  stats: { type: Object, required: true },
  processMode: { type: String, default: 'single' },
  hasValidSources: { type: Boolean, default: false },
  expandedGroups: { type: Object, default: () => ({}) },
  legadoExport: { type: Object, default: () => ({}) },
  legadoExportExpireText: { type: String, default: '' }
})

defineEmits([
  'toggle-group',
  'retry-failed',
  'export-failed',
  'download',
  'export-app',
  'restart'
])

const hasFailedCategories = computed(() =>
  props.sourceData.failedCategories &&
  Object.keys(props.sourceData.failedCategories).length > 0
)

const hasFailedGroups = computed(() =>
  Array.isArray(props.sourceData.failedGroups) &&
  props.sourceData.failedGroups.length > 0
)
</script>

<style scoped>
/* 规则类型统计样式 */
.rule-type-stats {
  margin-top: 20px;
  padding: 16px;
  background: var(--card-bg);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.rule-type-title {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: var(--text-primary);
}

.rule-type-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.rule-type-card {
  padding: 12px;
  border-radius: 8px;
  text-align: center;
}

.rule-type-card.search-only {
  background: rgba(64, 158, 255, 0.1);
  border: 1px solid rgba(64, 158, 255, 0.3);
}

.rule-type-card.explore-only {
  background: rgba(103, 194, 58, 0.1);
  border: 1px solid rgba(103, 194, 58, 0.3);
}

.rule-type-card.both {
  background: rgba(230, 162, 60, 0.1);
  border: 1px solid rgba(230, 162, 60, 0.3);
}

.rule-type-card.none {
  background: rgba(245, 108, 108, 0.1);
  border: 1px solid rgba(245, 108, 108, 0.3);
}

.rule-type-label {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.rule-type-numbers {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-bottom: 4px;
  font-size: 13px;
}

.rule-type-numbers .valid {
  color: #67c23a;
}

.rule-type-numbers .invalid {
  color: #f56c6c;
}

.rule-type-total {
  font-size: 12px;
  color: var(--text-muted);
}

/* 失败分组样式 */
.failed-groups {
  margin-top: 20px;
  padding: 16px;
  background: var(--failed-bg);
  border-radius: 8px;
  border: 1px solid var(--failed-border);
}

.failed-title {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: var(--failed-text);
}

.failed-list {
  max-height: 300px;
  overflow-y: auto;
}

.failed-item {
  border-bottom: 1px solid var(--failed-border);
}

.failed-item:last-child {
  border-bottom: none;
}

.failed-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.failed-header:hover {
  background: var(--bg-tertiary);
}

.failed-reason {
  flex: 1;
  font-weight: 500;
  color: var(--failed-text);
}

.failed-count {
  margin-right: 12px;
  color: var(--text-secondary);
  font-size: 14px;
}

.failed-toggle {
  color: var(--text-muted);
  font-size: 12px;
}

.failed-sources {
  padding: 8px 16px 12px;
  background: var(--card-bg);
}

.failed-source-item {
  display: flex;
  flex-direction: column;
  padding: 8px 0;
  border-bottom: 1px dashed var(--border-light);
}

.failed-source-item:last-child {
  border-bottom: none;
}

.source-name {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.source-url {
  font-size: 12px;
  color: var(--text-muted);
  word-break: break-all;
}

.failed-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.export-failed-btn,
.retry-failed-btn,
.retry-network-btn {
  width: 100%;
  padding: 10px;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.retry-failed-btn {
  background: #409eff;
}

.retry-network-btn {
  background: #67c23a;
}

.export-failed-btn {
  background: #ef5350;
}

.retry-failed-btn:hover {
  background: #337ecc;
}

.retry-network-btn:hover {
  background: #529b2e;
}

.export-failed-btn:hover {
  background: #d32f2f;
}

/* 重新处理按钮 */
.restart-btn {
  display: block;
  margin: 16px auto 0;
  padding: 12px 24px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 2px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.restart-btn:hover {
  border-color: #409eff;
  color: #409eff;
}

/* 移动端导出面板 */
.mobile-export-panel {
  margin-top: 16px;
  padding: 16px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  text-align: left;
}

.mobile-export-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.mobile-export-hint {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.mobile-export-status,
.mobile-export-expire {
  font-size: 12px;
  color: var(--text-muted);
}

.mobile-export-links {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.mobile-export-link {
  color: #409eff;
  text-decoration: none;
  word-break: break-all;
}

.mobile-export-link:hover {
  text-decoration: underline;
}

@media (max-width: 575px) {
  .rule-type-numbers {
    flex-direction: column;
    gap: 4px;
  }

  .failed-header {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .failed-reason {
    flex: 1 1 100%;
    text-align: left;
    word-break: break-word;
  }

  .failed-count {
    margin-right: 0;
  }

  .failed-actions {
    grid-template-columns: 1fr;
  }

  .mobile-export-panel {
    padding: 14px;
  }

  .mobile-export-links {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
