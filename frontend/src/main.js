import { createApp } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCheckbox,
  ElCheckboxGroup,
  ElIcon,
  ElInput,
  ElMessage,
  ElOption,
  ElProgress,
  ElSelect,
  ElTooltip
} from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import './styles/index.css'

const app = createApp(App)

app.use(ElAlert)
app.use(ElButton)
app.use(ElCheckbox)
app.use(ElCheckboxGroup)
app.use(ElIcon)
app.use(ElInput)
app.use(ElOption)
app.use(ElProgress)
app.use(ElSelect)
app.use(ElTooltip)

app.config.globalProperties.$message = ElMessage
app.mount('#app')
