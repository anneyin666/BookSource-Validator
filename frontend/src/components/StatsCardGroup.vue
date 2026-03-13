<template>
  <div class="stats-section">
    <div class="stats-card-group">
      <StatsCard
        :value="stats.total"
        label="总书源数"
        theme="primary"
      />
      <StatsCard
        :value="stats.dedupCount"
        label="去重后"
        theme="primary"
      />
      <StatsCard
        v-if="stats.duplicates > 0"
        :value="stats.duplicates"
        label="重复数"
        theme="warning"
      />
      <StatsCard
        :value="stats.formatInvalid"
        label="格式失效"
        theme="warning"
      />
      <StatsCard
        v-if="stats.deepInvalid !== null"
        :value="stats.deepInvalid"
        label="深度失效"
        theme="warning"
      />
    </div>
    <DuplicateUrls :duplicate-urls="stats.duplicateUrls" />
  </div>
</template>

<script setup>
import StatsCard from './StatsCard.vue'
import DuplicateUrls from './DuplicateUrls.vue'

defineProps({
  stats: {
    type: Object,
    required: true
  }
})
</script>

<style scoped>
.stats-section {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stats-card-group {
  display: flex;
  justify-content: center;
  gap: 24px;
  flex-wrap: wrap;
}

@media (max-width: 576px) {
  .stats-card-group {
    flex-direction: column;
    align-items: center;
  }
}
</style>