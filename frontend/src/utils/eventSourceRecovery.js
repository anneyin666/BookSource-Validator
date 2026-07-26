/**
 * Bind native EventSource reconnect notifications without closing the stream.
 *
 * EventSource reconnects automatically after transient network failures. This
 * helper only controls UI notifications and deliberately leaves the source
 * open so the browser can reconnect with the same validation session ID.
 */
export function bindEventSourceRecovery(source, options = {}) {
  const {
    isActive = () => true,
    onDisconnect = () => {},
    onReconnect = () => {}
  } = options
  let reconnecting = false

  source.onerror = () => {
    if (!isActive() || reconnecting) return
    reconnecting = true
    onDisconnect()
  }

  source.onopen = () => {
    if (!reconnecting) return
    reconnecting = false
    onReconnect()
  }
}
