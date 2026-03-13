<template>
  <button class="theme-toggle" @click="toggleTheme" :title="isDark ? '切换到亮色模式' : '切换到暗色模式'">
    <span class="theme-icon">{{ isDark ? '🌙' : '☀️' }}</span>
  </button>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const isDark = ref(false)

onMounted(() => {
  // 从 localStorage 读取主题设置
  const savedTheme = localStorage.getItem('sourceTool_theme')
  if (savedTheme === 'dark') {
    isDark.value = true
    document.documentElement.setAttribute('data-theme', 'dark')
  }
})

function toggleTheme() {
  isDark.value = !isDark.value
  if (isDark.value) {
    document.documentElement.setAttribute('data-theme', 'dark')
    localStorage.setItem('sourceTool_theme', 'dark')
  } else {
    document.documentElement.removeAttribute('data-theme')
    localStorage.setItem('sourceTool_theme', 'light')
  }
}
</script>

<style scoped>
.theme-toggle {
  position: fixed;
  top: 20px;
  right: 20px;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 2px solid var(--border-color);
  background: var(--card-bg);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px var(--shadow-color);
  transition: all 0.3s ease;
  z-index: 1000;
}

.theme-toggle:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 12px var(--shadow-color);
}

.theme-icon {
  font-size: 20px;
}

@media (max-width: 768px) {
  .theme-toggle {
    top: 12px;
    right: 12px;
    width: 40px;
    height: 40px;
  }
}
</style>