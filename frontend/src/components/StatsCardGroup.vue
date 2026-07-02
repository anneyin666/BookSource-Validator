<template>
  <div class="stats-section">
    <div class="stats-card-group">
      <div class="stats-row stats-row-primary">
        <StatsCard
          class="stat-card-main"
          :value="stats.total"
          label="总书源数"
          theme="primary"
        />
        <StatsCard
          class="stat-card-main"
          :value="stats.dedupCount"
          label="去重后"
          theme="primary"
        />
      </div>

      <div
        class="stats-row stats-row-secondary"
        :class="`items-${secondaryStatsCount}`"
      >
        <StatsCard
          v-if="stats.duplicates > 0"
          class="stat-card-secondary"
          :value="stats.duplicates"
          label="重复数"
          theme="warning"
        />
        <StatsCard
          class="stat-card-secondary"
          :value="stats.formatInvalid"
          label="格式失效"
          theme="warning"
        />
        <StatsCard
          v-if="stats.deepInvalid !== null"
          class="stat-card-secondary"
          :value="stats.deepInvalid"
          label="深度失效"
          theme="warning"
        />
      </div>
    </div>
    <DuplicateUrls :duplicate-urls="stats.duplicateUrls" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StatsCard from './StatsCard.vue'
import DuplicateUrls from './DuplicateUrls.vue'

const props = defineProps({
  stats: {
    type: Object,
    required: true
  }
})

const secondaryStatsCount = computed(() => {
  let count = 1 // formatInvalid is always rendered.
  if (props.stats.duplicates > 0) count += 1
  if (props.stats.deepInvalid !== null) count += 1
  return count
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

.stats-row {
  display: contents;
}

@media (max-width: 576px) {
  .stats-card-group {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    width: 100%;
  }

  .stats-row {
    display: grid;
    gap: 10px;
  }

  .stats-row-primary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stats-row-secondary {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .stats-row-secondary.items-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stats-row-secondary.items-1 {
    grid-template-columns: 1fr;
  }
}
</style>
