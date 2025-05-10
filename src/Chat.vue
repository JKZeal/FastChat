<template>
  <div class="chat-container">
    <el-container class="full-height">
      <!-- Header -->
      <el-header class="chat-header">
        <div class="header-content">
          <el-button :icon="Back" circle @click="goBack" aria-label="返回"></el-button>
          <div class="group-info">
            <h3>{{ groupInfo?.name || '聊天室' }}</h3>
            <p class="group-description">{{ groupInfo?.description || '暂无描述' }}</p>
          </div>
          <el-button :icon="UserIcon" circle @click="toggleMembersSider" aria-label="查看成员"></el-button>
        </div>
        <div class="connection-status">
          <span :class="{'connected': isConnected, 'disconnected': !isConnected}">
            {{ isConnected ? '已连接' : '连接中...' }}
          </span>
        </div>
      </el-header>

      <!-- Main Content (Chat Area and Members Sider) -->
      <el-container>
        <!-- Chat Area -->
        <el-main class="chat-area-main">
          <el-scrollbar ref="chatAreaScrollbar" class="chat-messages-scrollbar">
            <div class="messages-list">
              <div v-if="messages.length === 0" class="no-messages">
                成为第一个发言的人吧!
              </div>
              <div v-for="message in messages" :key="message.id"
                   :class="['message-item', message.sender?.username === localUsername ? 'sent' : 'received', `message-type-${message.message_type}`]">

                <!-- System Messages -->
                <div v-if="message.message_type === 'system'" class="system-message">
                  <span>{{ message.content }}</span>
                </div>

                <!-- User Messages -->
                <div v-else class="user-message-content">
                  <el-avatar v-if="message.sender?.username !== localUsername" class="avatar" :src="message.sender?.avatar_url || undefined">
                    {{ message.sender?.username?.charAt(0).toUpperCase() }}
                  </el-avatar>
                  <div class="message-bubble">
                    <div v-if="message.sender?.username !== localUsername" class="sender-name">
                      {{ message.sender?.username }}
                    </div>

                    <div v-if="message.message_type === 'text'" class="message-text">
                      {{ message.content }}
                    </div>
                    <div v-else-if="message.message_type === 'image' && message.file_url" class="message-image">
                      <el-image :src="message.file_url" :preview-src-list="[message.file_url]" fit="contain" style="max-width: 200px; max-height: 200px; border-radius: 4px;" alt="图片消息"></el-image>
                    </div>
                    <div v-else-if="message.message_type === 'file' && message.file_url" class="message-file">
                      <el-link :href="message.file_url" target="_blank" type="primary" :underline="false">
                        <el-icon><Paperclip /></el-icon> {{ message.file_name }} ({{ formatFileSize(message.file_size) }})
                      </el-link>
                    </div>
                    <div class="message-time">{{ formatTime(message.created_at) }}</div>
                  </div>
                   <el-avatar v-if="message.sender?.username === localUsername" class="avatar self-avatar" :src="message.sender?.avatar_url || undefined">
                    {{ message.sender?.username?.charAt(0).toUpperCase() }}
                  </el-avatar>
                </div>
              </div>
            </div>
          </el-scrollbar>
        </el-main>

        <!-- Members Sider -->
        <el-aside v-if="showMembersSider" width="250px" class="members-sider">
          <h4>群组成员 ({{ groupMembers.length }})</h4>
          <el-scrollbar>
            <ul class="members-list">
              <li v-for="member in groupMembers" :key="member.id" class="member-item">
                <el-avatar :src="member.avatar_url || undefined" size="small">
                  {{ member.username?.charAt(0).toUpperCase() }}
                </el-avatar>
                <span class="member-name">{{ member.username }}</span>
                <span class="member-status">{{ member.status || '在线' }}</span>
              </li>
            </ul>
          </el-scrollbar>
        </el-aside>
      </el-container>

      <!-- Footer (Input Area) -->
      <el-footer class="chat-input-area">
        <div class="input-actions">
          <el-tooltip content="发送图片 (待实现)" placement="top">
            <el-button :icon="PictureFilled" circle disabled @click="() => ElMessage.info('图片上传待实现')"></el-button>
          </el-tooltip>
          <el-tooltip content="发送文件 (待实现)" placement="top">
            <el-button :icon="PaperclipIcon" circle disabled @click="() => ElMessage.info('文件上传待实现')"></el-button>
          </el-tooltip>
        </div>
        <el-input
          v-model="newMessage"
          placeholder="输入消息..."
          @keyup.enter="sendMessage"
          clearable
          class="message-input"
        >
          <template #append>
            <el-button :icon="Promotion" @click="sendMessage" aria-label="发送"></el-button>
          </template>
        </el-input>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import axios from 'axios';
import { ElMessage, ElAvatar, ElScrollbar, ElContainer, ElHeader, ElMain, ElAside, ElFooter, ElButton, ElInput, ElLink, ElImage, ElIcon, ElTooltip } from 'element-plus';
import { Paperclip as PaperclipIcon, PictureFilled, Promotion, Back, User as UserIcon } from '@element-plus/icons-vue'; // Renamed Paperclip to avoid conflict

const route = useRoute();
const router = useRouter();

const groupId = ref(route.params.groupId);

const groupInfo = ref(null);
const messages = ref([]);
const newMessage = ref('');
const ws = ref(null);
const isConnected = ref(false);
const chatAreaScrollbar = ref(null);
const showMembersSider = ref(false);
const groupMembers = ref([]);

const localUsername = ref(localStorage.getItem('username'));

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const formatFileSize = (bytes) => {
  if (bytes === undefined || bytes === null || isNaN(bytes)) return 'N/A';
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const fetchGroupInfoAndMessages = async () => {
  const currentGroupId = groupId.value;
  if (!currentGroupId || currentGroupId === 'undefined' || isNaN(parseInt(currentGroupId))) {
    console.error('fetchGroupInfoAndMessages called with invalid group ID:', currentGroupId);
    ElMessage.error('无法加载聊天：群组ID无效。将返回群组列表。');
    router.push('/groups');
    return;
  }

  try {
    const groupResponse = await axios.get(`/api/groups/${currentGroupId}`);
    groupInfo.value = groupResponse.data;
    groupMembers.value = groupResponse.data.members || [];

    const messagesResponse = await axios.get(`/api/groups/${currentGroupId}/messages/`);
    messages.value = messagesResponse.data;
    scrollToBottom();
  } catch (error) {
    console.error(`获取群组 ${currentGroupId} 信息或消息失败:`, error);
    if (error.response?.status === 404) {
        ElMessage.error('群组不存在或您无权访问。');
    } else {
        ElMessage.error('获取群组信息或消息失败: ' + (error.response?.data?.detail || error.message));
    }
    router.push('/groups');
  }
};

const connectWebSocket = () => {
  const currentGroupId = groupId.value;
  if (!currentGroupId || currentGroupId === 'undefined' || isNaN(parseInt(currentGroupId))) {
      console.error('connectWebSocket called with invalid group ID:', currentGroupId);
      ElMessage.error('无法连接聊天服务：群组ID无效。');
      return;
  }

  const token = localStorage.getItem('token');
  if (!token) {
    ElMessage.error('用户未登录或会话已过期');
    router.push('/login');
    return;
  }

  const backendWsHost = 'localhost:8000';
  const wsUrl = `ws://${backendWsHost}/ws/chat?token=${token}&group_id=${currentGroupId}`;

  console.log(`尝试连接 WebSocket: ${wsUrl}`);
  ws.value = new WebSocket(wsUrl);

  ws.value.onopen = () => {
    isConnected.value = true;
    ElMessage.success(`已连接到群组: ${groupInfo.value?.name || '聊天室'}`);
    console.log('WebSocket 连接已打开');
  };

  ws.value.onmessage = (event) => {
    try {
      const messageData = JSON.parse(event.data);
      console.log('收到消息:', messageData);

      if (messageData.type === "connection_error") {
          ElMessage.error(`连接错误: ${messageData.error}`);
          isConnected.value = false;
          if (ws.value && ws.value.readyState === WebSocket.OPEN) {
              ws.value.close();
          }
          return;
      }

      if (messageData.type === "init_confirm") {
          console.log("WebSocket 初始化确认:", messageData.message);
          return;
      }

      messages.value.push(messageData);
      scrollToBottom();
    } catch (e) {
      console.error('解析消息错误:', e, event.data);
    }
  };

  ws.value.onerror = (error) => {
    console.error('WebSocket 错误:', error);
    ElMessage.error('WebSocket 连接发生错误。请检查网络连接和服务器状态。');
    isConnected.value = false;
  };

  ws.value.onclose = (event) => {
    console.log('WebSocket 连接已关闭:', event.code, event.reason);
    isConnected.value = false;
    if (event.code === 1000) {
        ElMessage.info('已离开聊天室。');
    } else if (event.reason) {
        ElMessage.warning(`连接已断开: ${event.reason}`);
    } else {
        ElMessage.warning('WebSocket 连接已断开。请尝试刷新或重新进入。');
    }
  };
};

const sendMessage = () => {
  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
    ElMessage.error('WebSocket 未连接，无法发送消息。');
    return;
  }
  if (newMessage.value.trim() === '') return;

  const messagePayload = {
    content: newMessage.value.trim(),
  };
  ws.value.send(JSON.stringify(messagePayload));
  newMessage.value = '';
};

const scrollToBottom = () => {
  nextTick(() => {
    const scrollbarEl = chatAreaScrollbar.value?.$el;
    if (scrollbarEl) {
      const wrap = scrollbarEl.querySelector('.el-scrollbar__wrap');
      if (wrap) {
        wrap.scrollTop = wrap.scrollHeight;
      }
    }
  });
};

const goBack = () => {
  router.push('/groups');
};

const toggleMembersSider = () => {
  showMembersSider.value = !showMembersSider.value;
  const currentGroupId = groupId.value;
  if (showMembersSider.value && groupInfo.value && (!groupMembers.value || groupMembers.value.length === 0) && currentGroupId && currentGroupId !== 'undefined' && !isNaN(parseInt(currentGroupId))) {
    axios.get(`/api/groups/${currentGroupId}`)
      .then(response => groupMembers.value = response.data.members || [])
      .catch(err => console.error("刷新成员列表失败", err));
  }
};

onMounted(async () => {
  const currentGroupId = groupId.value;
  console.log('Chat.vue mounted. route.params.groupId:', route.params.groupId, 'Ref groupId.value:', currentGroupId);

  if (!currentGroupId || currentGroupId === 'undefined' || isNaN(parseInt(currentGroupId))) {
    ElMessage.error('无效的群组ID。正在返回群组列表。');
    console.error('Invalid group ID detected in Chat.vue onMounted:', currentGroupId);
    router.push('/groups');
    return;
  }

  await fetchGroupInfoAndMessages();
  // connectWebSocket will only be called if fetchGroupInfoAndMessages succeeds
  // and groupInfo.value is populated. fetchGroupInfoAndMessages handles redirection on failure.
  if (groupInfo.value) {
    connectWebSocket();
  } else {
    console.warn("Group info not available after fetch, WebSocket connection skipped. Redirection should have occurred.");
  }
});

onBeforeUnmount(() => {
  if (ws.value && ws.value.readyState === WebSocket.OPEN) {
    ws.value.close(1000, "组件卸载");
  }
  ws.value = null;
});

</script>

<style scoped>
/* Styles from previous Chat.vue response, ensure they are complete */
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh; /* Ensure it takes full viewport height */
  width: 100%;
  overflow: hidden; /* Prevent main page scrollbars */
  background-color: #f0f2f5;
}

.full-height {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-header {
  background-color: #ffffff;
  border-bottom: 1px solid #e0e0e0;
  padding: 0 15px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  height: 60px;
}

.header-content {
  display: flex;
  align-items: center;
}

.group-info {
  margin-left: 15px;
  margin-right: 15px;
  text-align: left;
}

.group-info h3 {
  margin: 0;
  font-size: 1.1em;
  font-weight: 600;
}

.group-info .group-description {
  margin: 0;
  font-size: 0.8em;
  color: #606266;
}

.connection-status {
  font-size: 0.8em;
}
.connection-status .connected { color: #67c23a; }
.connection-status .disconnected { color: #f56c6c; }


.chat-area-main {
  padding: 0;
  flex-grow: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.chat-messages-scrollbar {
  width: 100%;
  height: 100%;
  background-color: #f9f9f9;
}
.messages-list {
  padding: 15px;
  display: flex;
  flex-direction: column;
}

.no-messages {
  text-align: center;
  color: #909399;
  margin-top: 20px;
  font-style: italic;
}

.message-item {
  display: flex;
  margin-bottom: 15px;
  max-width: 70%;
  align-items: flex-end;
}

.message-item.sent {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-item.received {
  align-self: flex-start;
}

.system-message {
  width: 100%;
  text-align: center;
  font-size: 0.8em;
  color: #909399;
  margin: 10px 0;
}

.user-message-content {
  display: flex;
  align-items: flex-end;
}
.message-item.sent .user-message-content {
  flex-direction: row-reverse;
}

.avatar {
  margin: 0 8px;
  flex-shrink: 0;
}

.message-bubble {
  padding: 8px 12px;
  border-radius: 10px;
  word-wrap: break-word;
  overflow-wrap: break-word;
  text-align: left;
}

.message-item.sent .message-bubble {
  background-color: #409eff;
  color: white;
  border-bottom-right-radius: 2px;
}

.message-item.received .message-bubble {
  background-color: #e4e6eb;
  color: #303133;
  border-bottom-left-radius: 2px;
}

.sender-name {
  font-size: 0.75em;
  font-weight: bold;
  margin-bottom: 3px;
  color: #606266;
}
.message-item.sent .sender-name {
  display: none;
}

.message-text {
  white-space: pre-wrap;
}
.message-image img { /* el-image renders an img tag inside */
  max-width: 200px;
  max-height: 200px;
  border-radius: 5px;
  cursor: pointer;
  display: block; /* Ensure proper rendering of el-image */
}
.message-file a {
  color: inherit;
}
.message-item.sent .message-file a {
  color: white;
}
.message-item.received .message-file a {
  color: #409eff;
}
.message-item.received .message-file .el-icon {
  color: #409eff; /* Ensure icon color matches link */
}


.message-time {
  font-size: 0.7em;
  margin-top: 4px;
  text-align: right;
  color: rgba(0,0,0,0.4);
}
.message-item.sent .message-time {
  color: rgba(255,255,255,0.7);
}


.members-sider {
  border-left: 1px solid #e0e0e0;
  padding: 15px;
  background-color: #fff;
  flex-shrink: 0;
}
.members-sider h4 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 1em;
}
.members-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.member-item {
  display: flex;
  align-items: center;
  padding: 8px 0;
  font-size: 0.9em;
}
.member-name {
  margin-left: 8px;
  flex-grow: 1;
}
.member-status {
  font-size: 0.8em;
  color: #909399;
}

.chat-input-area {
  display: flex;
  align-items: center;
  padding: 10px 15px;
  background-color: #ffffff;
  border-top: 1px solid #e0e0e0;
  flex-shrink: 0;
  height: auto;
}
.input-actions {
  margin-right: 10px;
}
.message-input {
  flex-grow: 1;
}
</style>