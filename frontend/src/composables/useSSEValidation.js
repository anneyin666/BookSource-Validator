// SSE 校验订阅组合式函数
// 统一处理：进度解析、完成/取消/错误分支、断线恢复、强制重连看门狗、耗时计时。
//
// 移动端弱网/后台切换场景下，原生 EventSource 可能出现：
// 1. 连接被运营商 NAT/代理静默掐断，onerror 不触发（消息停滞）
// 2. 浏览器后台挂起后 readyState 变为 CLOSED，不再自动重连
// 3. 网络切换（WiFi <-> 流量）后连接失效
// 看门狗通过消息停滞检测 + visibilitychange/online 监听覆盖以上情况，
// 重建连接时复用同一 sessionId，后端 runner 独立运行并重放终态结果。
import { ref } from 'vue'
import { bindEventSourceRecovery } from '../utils/eventSourceRecovery.js'

// 超过该时长未收到任何 SSE 消息视为连接已死（正常进度每 0.3s 一条）
const STALL_THRESHOLD_MS = 15000
// 看门狗巡检间隔
const WATCHDOG_INTERVAL_MS = 5000

/**
 * SSE 校验订阅
 * @param {Object} options
 * @param {(label: string) => void} options.onDisconnect 断线通知（含强制重连）
 * @param {(label: string) => void} options.onReconnect 恢复通知
 */
export function useSSEValidation(options = {}) {
  const {
    onDisconnect = () => {},
    onReconnect = () => {}
  } = options

  const progressData = ref(null)
  const elapsedTime = ref(0)

  let eventSource = null
  let createSourceFn = null
  let handlers = null
  let label = '校验'
  let lastMessageAt = 0
  let watchdogTimer = null
  let timerInterval = null

  function isActive() {
    return !!eventSource && !!handlers
  }

  function closeEventSource() {
    if (!eventSource) return
    // 先清空回调再关闭，避免触发 onerror 误报断线
    eventSource.onerror = null
    eventSource.onopen = null
    eventSource.onmessage = null
    eventSource.close()
    eventSource = null
  }

  function startTimer() {
    elapsedTime.value = 0
    if (timerInterval) clearInterval(timerInterval)
    timerInterval = setInterval(() => {
      elapsedTime.value++
    }, 1000)
  }

  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval)
      timerInterval = null
    }
  }

  function markReconnecting() {
    if (progressData.value && progressData.value.status !== 'reconnecting') {
      progressData.value = { ...progressData.value, status: 'reconnecting' }
    }
  }

  function forceReconnect(reason) {
    if (!isActive() || !createSourceFn) return
    console.warn(`[SSE] 连接异常，强制重建(${reason}): ${label}`)
    markReconnecting()
    closeEventSource()
    attach(createSourceFn())
    onDisconnect(label)
  }

  function attach(source) {
    eventSource = source
    lastMessageAt = Date.now()

    bindEventSourceRecovery(source, {
      isActive: () => source === eventSource && isActive(),
      onDisconnect: () => {
        markReconnecting()
        onDisconnect(label)
      },
      onReconnect: () => {
        if (progressData.value?.status === 'reconnecting') {
          progressData.value = { ...progressData.value, status: 'running' }
        }
        onReconnect(label)
      }
    })

    source.onmessage = (event) => {
      lastMessageAt = Date.now()

      let data
      try {
        data = JSON.parse(event.data)
      } catch (err) {
        console.warn('[SSE] 无法解析消息:', event.data)
        return
      }

      if (!handlers) return

      if (data.error) {
        const { onError } = handlers
        cleanup()
        onError(data.error)
        return
      }

      if (data.status === 'completed' && data.validCount !== undefined) {
        const { onCompleted } = handlers
        cleanup()
        onCompleted(data)
        return
      }

      if (data.status === 'cancelled') {
        const { onCancelled } = handlers
        cleanup()
        onCancelled(data)
        return
      }

      progressData.value = {
        processed: data.processed,
        total: data.total,
        valid: data.valid,
        invalid: data.invalid,
        current: data.current,
        currentName: data.currentName || '',
        estimatedRemaining: data.estimatedRemaining || 0,
        status: data.status || 'running',
        strategy: data.strategy || null
      }
    }
  }

  function startWatchdog() {
    if (watchdogTimer) return
    watchdogTimer = setInterval(() => {
      if (!isActive() || !eventSource) return

      const isClosed = eventSource.readyState === EventSource.CLOSED
      // 页面不可见时浏览器会节流定时器，只在可见或连接已死时处理
      if (document.visibilityState !== 'visible' && !isClosed) return

      const stalled = Date.now() - lastMessageAt > STALL_THRESHOLD_MS
      if (isClosed) {
        forceReconnect('closed')
      } else if (stalled) {
        forceReconnect('stall')
      }
    }, WATCHDOG_INTERVAL_MS)
  }

  function handleVisibilityChange() {
    if (document.visibilityState !== 'visible' || !isActive() || !eventSource) return
    // 从后台切回：连接可能已被系统静默掐断，若非 OPEN 立即重建
    if (eventSource.readyState !== EventSource.OPEN) {
      forceReconnect('visibility')
      return
    }
    // OPEN 状态但长时间无消息，同样重建
    if (Date.now() - lastMessageAt > STALL_THRESHOLD_MS) {
      forceReconnect('visibility-stall')
    }
  }

  function handleOnline() {
    if (!isActive() || !eventSource) return
    if (eventSource.readyState !== EventSource.OPEN || Date.now() - lastMessageAt > STALL_THRESHOLD_MS) {
      forceReconnect('online')
    }
  }

  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.addEventListener('online', handleOnline)

  /**
   * 订阅一次校验会话的 SSE 进度
   * @param {Object} config
   * @param {() => EventSource} config.createSource EventSource 工厂（重连时复用）
   * @param {string} [config.label] 提示文案前缀
   * @param {Object} [config.initialProgress] 初始进度（如 { total: 100 }）
   * @param {(data: Object) => void} config.onCompleted 校验完成（含有效结果）
   * @param {(data: Object) => void} config.onCancelled 校验取消（data.validCount 可能不存在）
   * @param {(message: string) => void} config.onError 会话错误
   */
  function subscribe({
    createSource,
    label: sourceLabel = '校验',
    initialProgress = null,
    onCompleted,
    onCancelled,
    onError
  }) {
    closeEventSource()
    handlers = { onCompleted, onCancelled, onError }
    label = sourceLabel
    createSourceFn = createSource

    if (initialProgress) {
      progressData.value = {
        processed: 0,
        valid: 0,
        invalid: 0,
        current: '',
        currentName: '',
        estimatedRemaining: 0,
        status: 'running',
        ...initialProgress
      }
    }

    startTimer()
    attach(createSource())
    startWatchdog()
  }

  /** 结束订阅：关闭连接与计时器（进度数据保留，由调用方决定是否重置） */
  function cleanup() {
    closeEventSource()
    handlers = null
    createSourceFn = null
    stopTimer()
  }

  /** 彻底销毁：清理看门狗与全局监听（组件卸载时调用） */
  function destroy() {
    cleanup()
    progressData.value = null
    if (watchdogTimer) {
      clearInterval(watchdogTimer)
      watchdogTimer = null
    }
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    window.removeEventListener('online', handleOnline)
  }

  return {
    progressData,
    elapsedTime,
    subscribe,
    stop: cleanup,
    destroy
  }
}
