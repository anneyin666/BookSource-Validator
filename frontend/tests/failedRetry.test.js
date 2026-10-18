/** Tests for failed-source retry helpers. */

import assert from 'node:assert/strict'
import test from 'node:test'

import { useFailedRetry } from '../src/composables/useFailedRetry.js'

const {
  isRetryableGroup,
  collectFailedSources,
  mergeRetryResultData
} = useFailedRetry()


test('prefers backend category over reason keywords', () => {
  assert.equal(isRetryableGroup({ reason: '超时', category: 'fixable' }), true)
  assert.equal(isRetryableGroup({ reason: '超时', category: 'checkable' }), false)
})

test('falls back to keyword matching for legacy groups', () => {
  assert.equal(isRetryableGroup({ reason: '连接失败' }), true)
  assert.equal(isRetryableGroup({ reason: 'HTTP 404' }), false)
})

test('collects retry sources and keeps skipped groups', () => {
  const sourceData = {
    failedGroups: [
      {
        reason: '连接失败',
        category: 'fixable',
        count: 2,
        sources: [
          { bookSourceName: 'a', bookSourceUrl: 'https://a.com' },
          { name: 'b', url: 'https://b.com' }
        ]
      },
      {
        reason: 'HTTP 404',
        category: 'checkable',
        count: 1,
        sources: [{ bookSourceName: 'c', bookSourceUrl: 'https://c.com' }]
      }
    ]
  }

  const { retrySources, skippedGroups } = collectFailedSources(sourceData, true)

  assert.equal(retrySources.length, 2)
  assert.equal(retrySources[0].bookSourceName, 'a')
  assert.equal(retrySources[1].bookSourceUrl, 'https://b.com')
  assert.equal(retrySources[1].bookSourceName, 'b')
  assert.equal(skippedGroups.length, 1)
  assert.equal(skippedGroups[0].reason, 'HTTP 404')
})

test('merges retry results and keeps skipped failures', () => {
  const previous = {
    total: 10,
    validCount: 1,
    deepInvalid: 2,
    dedupedSources: [{ bookSourceName: 'old', bookSourceUrl: 'https://old.com' }],
    failedGroups: [
      { reason: '连接失败', count: 1, sources: [{}] },
      { reason: 'HTTP 404', count: 1, sources: [{}] }
    ],
    failedCategories: { fixable: [{}] }
  }

  const retryData = {
    validCount: 1,
    invalidCount: 1,
    validSources: [{ bookSourceName: 'new', bookSourceUrl: 'https://new.com' }],
    failedGroups: [{ reason: '连接失败', count: 1, sources: [{}] }],
    failedCategories: { fixable: [{}] },
    ruleTypeStats: null
  }

  const merged = mergeRetryResultData(
    previous,
    retryData,
    [{ reason: 'HTTP 404', count: 1, sources: [{}] }]
  )

  assert.equal(merged.validCount, 2)
  assert.equal(merged.dedupedSources.length, 2)
  assert.equal(merged.deepInvalid, 2)
  assert.equal(merged.failedGroups.length, 2)
})
