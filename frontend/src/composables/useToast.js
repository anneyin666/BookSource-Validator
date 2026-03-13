// Toast 提示组合函数
import { ElMessage } from 'element-plus'

/**
 * Toast 提示组合函数
 * 基于 Element Plus ElMessage 封装
 */
export function useToast() {
  /**
   * 显示成功提示
   * @param {string} message - 提示消息
   */
  const showSuccess = (message) => {
    ElMessage.success({
      message,
      duration: 2000,
      showClose: true
    })
  }

  /**
   * 显示错误提示
   * @param {string} message - 提示消息
   */
  const showError = (message) => {
    ElMessage.error({
      message,
      duration: 3000,
      showClose: true
    })
  }

  /**
   * 显示警告提示
   * @param {string} message - 提示消息
   */
  const showWarning = (message) => {
    ElMessage.warning({
      message,
      duration: 2500,
      showClose: true
    })
  }

  /**
   * 显示信息提示
   * @param {string} message - 提示消息
   */
  const showInfo = (message) => {
    ElMessage.info({
      message,
      duration: 2000,
      showClose: true
    })
  }

  return {
    showSuccess,
    showError,
    showWarning,
    showInfo
  }
}