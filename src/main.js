import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import axios from 'axios'
import 'animate.css';
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

// 配置axios默认URL
axios.defaults.baseURL = '/'

// 添加请求拦截器
axios.interceptors.request.use(config => {
  // 从localStorage获取token
  const token = localStorage.getItem('token')
  if (token) {
    // 为请求添加Authorization头
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
}, error => {
  return Promise.reject(error)
})

// 添加响应拦截器处理401错误(token过期)
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      // token无效或过期，清除本地存储并重定向到登录页
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

const app = createApp(App)
const fixResponsiveStyles = `
  .container, .container-fluid, .container-lg, .container-md, 
  .container-sm, .container-xl, .container-xxl {
    width: 100%;
    max-width: 100%;
  }
  
  .el-card, .el-card__body {
    width: 100%;
  }
  
  .el-input, .el-input-group {
    width: 100%;
  }
`;

// 创建全局样式元素
const styleElement = document.createElement('style');
styleElement.textContent = fixResponsiveStyles;
document.head.appendChild(styleElement);
// 使用Element Plus
app.use(ElementPlus, {
  locale: zhCn // 使用中文
})

// 使用路由
app.use(router)
app.mount('#app')

// import { nextTick } from 'vue'
// app.use(router)
// router.isReady().then(() => {
//   app.mount('#app')
//   if (window.location.pathname === '/' || window.location.pathname === '') {
//     const token = localStorage.getItem('token')
//     if (token) {
//       router.replace('/groups')
//     } else {
//       router.replace('/login')
//     }
//   }
// })