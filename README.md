# FastChat 网络聊天室

## 项目简介

FastChat是一个基于Python和Vue技术的B/S架构的多媒体聊天应用，具有基本的账号管理和群组聊天功能，可在各种设备上流畅运行。

## 开发环境
- 操作系统: Windows 11 24H2
- 运行时: CPython 3.12, Node.js 22.14
- 包管理: Winget, pip, npm
- 

## 技术栈

### 前端
- Vue.js 3 (组合式API)
- Element Plus UI组件库
- WebSocket实时通信
- Vite构建工具

### 后端
- FastAPI
- SQLite数据库 (WAL模式)
- JWT认证保障API安全访问
- WebSocket实时通信

### 部署
- Cloudflare Tunnel隧道部署，实现公网访问

## 核心功能

- 账号管理(注册与登录)
- 个人资料管理(头像、个人简介)
- 群组管理(创建,查找,加入,退出)
- 实时消息收发（文本、图片、视频）
- 响应式UI设计（支持PC、手机）

## 项目亮点

1. **实时通讯**: 利用WebSocket技术实现消息的即时传递，无需手动刷新页面

2. **响应式设计**: 针对不同设备尺寸优化界面布局，实现移动端和桌面端的完美适配

3. **多媒体支持**: 支持发送嵌入式图片、Bilibili/YouTube的嵌入式视频

4. **数据库并发**: 使用SQLite的WAL模式增强并发性能

5. **无需备案**: 通过Cloudflare Tunnel实现内网应用的临时公网访问


## 未来规划 (也许明天开始做,也许永远不做了)

- 端到端加密
- 文件上传功能
- 私聊功能
- 自定义主题
- LLM助手集成
- TTS和SVC功能
- and so on...

---