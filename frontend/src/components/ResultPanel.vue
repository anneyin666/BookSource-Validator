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
