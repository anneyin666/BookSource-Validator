/** Tests for native EventSource reconnect behavior. */

import assert from 'node:assert/strict'
import test from 'node:test'

import { bindEventSourceRecovery } from '../src/utils/eventSourceRecovery.js'


class FakeEventSource {
  constructor() {
    this.closeCalls = 0
    this.onerror = null
    this.onopen = null
  }

  close() {
    this.closeCalls += 1
  }
}


test('keeps EventSource open and reports one disconnect until recovery', () => {
  const source = new FakeEventSource()
  let disconnects = 0
  let reconnects = 0

  bindEventSourceRecovery(source, {
    isActive: () => true,
    onDisconnect: () => {
      disconnects += 1
    },
    onReconnect: () => {
      reconnects += 1
    }
  })

  source.onerror()
  source.onerror()

  assert.equal(source.closeCalls, 0)
  assert.equal(disconnects, 1)
  assert.equal(reconnects, 0)

  source.onopen()
  source.onopen()

  assert.equal(reconnects, 1)
})


test('ignores disconnect after validation is no longer active', () => {
  const source = new FakeEventSource()
  let disconnects = 0

  bindEventSourceRecovery(source, {
    isActive: () => false,
    onDisconnect: () => {
      disconnects += 1
    }
  })

  source.onerror()

  assert.equal(disconnects, 0)
  assert.equal(source.closeCalls, 0)
})
