<template>
  <div class="chat-container">
    <!-- 三栏布局 -->
    <el-container class="full-height">
      <!-- 左侧：群组列表 -->
      <el-aside :width="isMobile ? '0' : '200px'" class="group-sidebar" :class="{ 'mobile-visible': isMobile && showGroupSidebar }">
        <div class="sidebar-header">
          <div class="user-info">
            <el-avatar :size="32" :src="userProfile.avatar_url || '/avatar/avatar0.png'"></el-avatar>
            <div class="user-name-container">
              <span class="username">{{ userProfile.username }}</span>
            </div>
          </div>
          <el-button type="primary" :icon="Back" size="small" @click="goToGroups">返回</el-button>
        </div>

        <div class="group-list">
          <h3>我的群组</h3>
          <template v-if="myGroups.length > 0">
            <div
              v-for="group in myGroups"
              :key="group.id"
              class="group-item"
              :class="{ active: group.id === parseInt(groupId) }"
              @click="switchGroup(group.id)"
            >
              <div class="group-id">#{{ group.id }}</div>
              <div class="group-name">{{ group.name }}</div>
            </div>
          </template>
          <div v-else class="no-groups">
            暂无群组
          </div>
        </div>
      </el-aside>

      <!-- 中部：聊天区域 -->
      <el-main class="chat-area">
        <!-- 移动端导航栏 -->
        <div v-if="isMobile" class="mobile-nav">
          <el-button link :icon="Menu" @click.stop="toggleSidebar('group')" />
          <div class="chat-group-title">{{ groupInfo?.name || '聊天室' }}</div>
          <el-button link :icon="User" @click.stop="toggleSidebar('members')" />
        </div>

        <!-- 消息区域 -->
        <el-scrollbar ref="chatAreaScrollbar" class="message-wrapper">
          <template v-if="messages.length > 0">
            <div v-for="(msg, index) in messages" :key="index">
              <!-- 系统消息 -->
              <div v-if="msg.sender.username === 'system'" class="system-message">
                {{ msg.content }}
              </div>
              <!-- 普通消息 -->
              <div v-else class="message" :class="msg.sender.username === localUsername ? 'my-message' : 'other-message'">
                <el-avatar class="message-avatar" :size="36" :src="msg.sender.avatar_url || '/avatar/avatar0.png'"></el-avatar>
                <div class="message-content">
                  <div class="message-username">{{ msg.sender.username }}</div>
                  <!-- 渲染消息内容，支持HTML渲染 -->
                  <div class="message-bubble" v-html="msg.content"></div>
                  <div class="message-time">{{ formatTime(msg.created_at) }}</div>
                </div>
              </div>
            </div>
          </template>
          <div v-else class="empty-chat">
            暂无消息，发送第一条消息开始聊天吧！
          </div>
        </el-scrollbar>

        <!-- 输入区域 -->
        <div class="chat-input-area">
          <div class="input-actions">
            <!-- Emoji按钮 -->
            <el-popover
              placement="top"
              width="300"
              trigger="click">
              <template #reference>
                <el-button type="primary" plain class="emoji-button">😊</el-button>
              </template>
              <div class="emoji-picker">
                <div
                  v-for="emoji in commonEmojis"
                  :key="emoji"
                  class="emoji-item"
                  @click="insertEmoji(emoji)"
                >
                  {{ emoji }}
                </div>
              </div>
            </el-popover>

            <!-- 图片按钮 -->
            <el-popover
              placement="top"
              width="400"
              trigger="click">
              <template #reference>
                <el-button :icon="Picture" type="primary" plain></el-button>
              </template>
              <div class="image-url-input">
                <el-input v-model="imageUrl" placeholder="输入图片URL" size="small"></el-input>
                <div class="popover-footer">
                  <el-button type="primary" size="small" @click="insertImageUrl">插入</el-button>
                </div>
              </div>
            </el-popover>

            <!-- 视频按钮 -->
            <el-popover
              placement="top"
              width="400"
              trigger="click">
              <template #reference>
                <el-button :icon="VideoPlay" type="primary" plain></el-button>
              </template>
              <div class="video-url-input">
                <el-input v-model="videoUrl" placeholder="输入Bilibili或YouTube视频链接" size="small"></el-input>
                <div class="popover-footer">
                  <el-button type="primary" size="small" @click="insertVideoUrl">插入</el-button>
                </div>
              </div>
            </el-popover>
          </div>

          <div class="message-input-container">
            <el-input
              v-model="newMessage"
              type="textarea"
              :rows="isMobile ? 2 : 3"
              resize="none"
              placeholder="请输入消息, 支持图片和视频嵌入...(Shift+Enter换行; Enter发送 )"
              class="message-input"
              @keyup.shift.enter.prevent
              @keyup.enter="handleEnterKey"
            >
            </el-input>
            <el-button type="primary" @click="sendMessage" class="send-button">发送</el-button>
          </div>
        </div>
      </el-main>

      <!-- 右侧：成员列表 -->
      <el-aside :width="isMobile ? '0' : '200px'" class="members-list" :class="{ 'mobile-visible': isMobile && showMembersSidebar }">
        <div class="members-header">
          <h3>成员列表 ({{ groupMembers.length }})</h3>
          <el-button v-if="isMobile" link :icon="Close" @click.stop="toggleSidebar('members')" />
        </div>
        <div class="members-container">
          <div v-for="member in sortedMembers" :key="member.id" class="member-item">
            <el-avatar :size="32" :src="member.avatar_url || '/avatar/avatar0.png'"></el-avatar>
            <div class="member-info">
              <span class="member-name">{{ member.username }}</span>
            </div>
          </div>
          <div v-if="groupMembers.length === 0" class="no-members">
            暂无成员信息
          </div>
        </div>
      </el-aside>
    </el-container>

    <!-- 图片预览覆盖层 -->
    <div v-if="imagePreviewVisible" class="image-preview-overlay" @click="closePreview">
      <img :src="previewingImage" class="preview-image" @click.stop />
    </div>

    <!-- 侧边栏遮罩层 - 用于移动端 -->
    <div
      v-if="isMobile && (showGroupSidebar || showMembersSidebar)"
      class="sidebar-overlay"
      @click="closeAllSidebars"
    ></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import axios from 'axios';
import { ElMessage } from 'element-plus';
import { Back, Picture, VideoPlay, Menu, User, Close } from '@element-plus/icons-vue';

// ========== 响应式设计相关 ==========
const windowWidth = ref(window.innerWidth);
const isMobile = computed(() => windowWidth.value < 768);
const isTablet = computed(() => windowWidth.value >= 768 && windowWidth.value < 992);

const showGroupSidebar = ref(false);
const showMembersSidebar = ref(false);

const updateWindowWidth = () => {
  windowWidth.value = window.innerWidth;
  // 在非移动设备上，自动隐藏侧边栏
  if (!isMobile.value) {
    showGroupSidebar.value = false;
    showMembersSidebar.value = false;
  }
};

// 切换侧边栏显示
const toggleSidebar = (type) => {
  if (type === 'group') {
    showGroupSidebar.value = !showGroupSidebar.value;
    if (showGroupSidebar.value) {
      showMembersSidebar.value = false; // 确保只有一个侧边栏打开
    }
  } else if (type === 'members') {
    showMembersSidebar.value = !showMembersSidebar.value;
    if (showMembersSidebar.value) {
      showGroupSidebar.value = false; // 确保只有一个侧边栏打开
    }
  }
};

// 关闭所有侧边栏
const closeAllSidebars = () => {
  showGroupSidebar.value = false;
  showMembersSidebar.value = false;
};

// ========== 路由相关 ==========
const route = useRoute();
const router = useRouter();
const groupId = ref(route.params.groupId);

// ========== 状态变量 ==========
// 用户和群组信息
const groupInfo = ref(null);
const userProfile = ref({
  username: '',
  avatar_url: '',
  bio: ''
});
const localUsername = ref(localStorage.getItem('username'));
const groupMembers = ref([]);
const myGroups = ref([]);

// 聊天相关
const messages = ref([]);
const newMessage = ref('');
const chatAreaScrollbar = ref(null);

// WebSocket相关
const ws = ref(null);
const isConnected = ref(false);
const reconnectTimer = ref(null);
const shouldReconnect = ref(true);
const currentConnectedGroupId = ref(null);

// 图片相关
const imageUrl = ref('');
const imagePreviewVisible = ref(false);
const previewingImage = ref('');

// 视频相关
const videoUrl = ref('');

// Emoji相关
const commonEmojis = ref([
  '😊','😂','🤗','🤓','😎','😘','🤔',
  '😭','😄','😴','😡','🙌','👏','👍',
  '🙏','👀','❤️','🎉','🔥','💯','🌟',
]);

// ========== 计算属性 ==========
// 按用户名排序的成员列表
const sortedMembers = computed(() => {
  return [...groupMembers.value].sort((a, b) => {
    return a.username.localeCompare(b.username);
  });
});

// ========== 消息处理函数 ==========
// 格式化时间显示
const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${hours}:${minutes}`;
};

// ========== 图片处理函数 ==========
// 检查URL是否是有效的图片URL
const isValidImageUrl = (url) => {
  if (!url) return false;

  try {
    const parsedUrl = new URL(url);
    // 检查常见图片扩展名
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'];
    return imageExtensions.some(ext => parsedUrl.pathname.toLowerCase().endsWith(ext));
  } catch (e) {
    return false; // 不是有效的URL
  }
};

// 插入图片HTML到消息输入框
const insertImageUrl = () => {
  if (imageUrl.value.trim()) {
    const imgTag = `<img src="${imageUrl.value.trim()}" onclick="window.previewImage('${imageUrl.value.trim()}')">`;
    newMessage.value += newMessage.value ? '\n' + imgTag : imgTag;
    imageUrl.value = '';
  }
};

// 关闭预览
const closePreview = () => {
  imagePreviewVisible.value = false;
};

// 全局预览图片方法，供内联onclick使用
window.previewImage = (url) => {
  previewingImage.value = url;
  imagePreviewVisible.value = true;
};

// ========== 视频处理函数 ==========
// 将Bilibili链接转换为嵌入代码
const convertBilibiliUrl = (url) => {
  // 从B站链接提取BV号
  const bvMatch = url.match(/\/(?:video\/)(BV[a-zA-Z0-9]+)/);
  if (bvMatch && bvMatch[1]) {
    const bvid = bvMatch[1];
    return `<iframe src="//player.bilibili.com/player.html?bvid=${bvid}&page=1" scrolling="no" border="0" frameborder="no" framespacing="0" allowfullscreen="true" style="width: 100%; height: 360px;"></iframe>`;
  }
  return null;
};

// 将YouTube链接转换为嵌入代码
const convertYoutubeUrl = (url) => {
  // 处理不同格式的YouTube链接
  let videoId;

  // 标准格式 https://www.youtube.com/watch?v=VIDEO_ID
  const standardMatch = url.match(/youtube\.com\/watch\?v=([^&]+)/);
  if (standardMatch) {
    videoId = standardMatch[1];
  } else {
    // 短链接格式 https://youtu.be/VIDEO_ID
    const shortMatch = url.match(/youtu\.be\/([^?&]+)/);
    if (shortMatch) {
      videoId = shortMatch[1];
    }
  }

  if (videoId) {
    return `<iframe width="100%" height="315" src="https://www.youtube.com/embed/${videoId}" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>`;
  }
  return null;
};

// 插入视频嵌入代码到消息输入框
const insertVideoUrl = () => {
  if (!videoUrl.value.trim()) return;

  let embedCode = null;

  // 检查是否是Bilibili链接
  if (videoUrl.value.includes('bilibili.com')) {
    embedCode = convertBilibiliUrl(videoUrl.value);
  }
  // 检查是否是YouTube链接
  else if (videoUrl.value.includes('youtube.com') || videoUrl.value.includes('youtu.be')) {
    embedCode = convertYoutubeUrl(videoUrl.value);
  }

  if (embedCode) {
    newMessage.value += newMessage.value ? '\n' + embedCode : embedCode;
    videoUrl.value = '';
  } else {
    ElMessage.warning('无法识别的视频链接格式');
  }
};

// ========== Emoji处理函数 ==========
// 插入表情符号到消息输入框
const insertEmoji = (emoji) => {
  newMessage.value += emoji;
};

// ========== 输入处理函数 ==========
// 处理Enter键
const handleEnterKey = (e) => {
  // 如果按下Shift+Enter，则不发送消息，允许换行
  if (e.shiftKey) {
    return;
  }
  // 否则发送消息
  e.preventDefault();
  sendMessage();
};

// 发送消息
const sendMessage = () => {
  // 检查连接状态和消息内容
  if (!isConnected.value) {
    ElMessage.warning('未连接到服务器，无法发送消息');
    return;
  }

  const message = newMessage.value.trim();
  if (!message) return;

  const messageObj = {
    type: 'chat_message',
    content: message,
    group_id: groupId.value
  };

  try {
    // 发送给服务器
    ws.value.send(JSON.stringify(messageObj));
    // 清空输入
    newMessage.value = '';
    // 发送后关闭移动端侧边栏
    if (isMobile.value) {
      closeAllSidebars();
    }
  } catch (e) {
    console.error('发送消息失败:', e);
    ElMessage.error('发送消息失败');
  }
};

// ========== 数据获取函数 ==========
// 获取用户个人信息
const fetchUserProfile = async () => {
  try {
    const response = await axios.get('/api/users/me/');
    userProfile.value = response.data;
    return response.data;
  } catch (error) {
    console.error('获取用户信息失败:', error);
    if (error.response && error.response.status === 401) {
      router.push('/login');
    }
    return null;
  }
};

// 获取我的群组列表
const fetchMyGroups = async () => {
  try {
    const response = await axios.get('/api/groups/');
    myGroups.value = response.data;
    return response.data;
  } catch (error) {
    console.error('获取群组列表失败:', error);
    return [];
  }
};

// 获取群组信息和消息历史
const fetchGroupInfoAndMessages = async () => {
  try {
    // 获取群组详情
    const groupResponse = await axios.get(`/api/groups/${groupId.value}`);
    groupInfo.value = groupResponse.data;
    groupMembers.value = groupResponse.data.members || [];

    // 获取消息历史
    const messagesResponse = await axios.get(`/api/groups/${groupId.value}/messages/?limit=100`);
    messages.value = messagesResponse.data;

    // 滚动到底部
    scrollToBottom();
    return true;
  } catch (error) {
    console.error('获取群组信息或消息失败:', error);
    ElMessage.error('获取群组信息失败');
    return false;
  }
};

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (chatAreaScrollbar.value) {
      // 滚动到底部
      const scrollbar = chatAreaScrollbar.value;
      scrollbar.setScrollTop(scrollbar.$el.scrollHeight);
    }
  });
};

// ========== WebSocket相关函数 ==========
// 清除重连计时器
const clearReconnectTimer = () => {
  if (reconnectTimer.value) {
    clearTimeout(reconnectTimer.value);
    reconnectTimer.value = null;
  }
};

// 连接WebSocket
const connectWebSocket = () => {
  // 关闭旧的WebSocket连接
  if (ws.value) {
    shouldReconnect.value = false; // 设置为不自动重连
    if (ws.value.readyState === WebSocket.OPEN || ws.value.readyState === WebSocket.CONNECTING) {
      console.log('主动关闭旧的WebSocket连接');
      ws.value.close();
    }
    ws.value = null;
  }

  // 延迟一下再连接，确保前一个连接已关闭
  setTimeout(() => {
    shouldReconnect.value = true; // 恢复自动重连标志

    // 获取认证token
    const token = localStorage.getItem('token');
    if (!token) {
      ElMessage.error('未找到登录信息，请重新登录');
      router.push('/login');
      return;
    }

    // 创建新的WebSocket连接，添加token用于认证
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${window.location.host}/ws/chat?group_id=${groupId.value}&token=${token}`;

    console.log(`正在连接到WebSocket: ${wsUrl} (群组ID: ${groupId.value})`);
    ws.value = new WebSocket(wsUrl);

    ws.value.onopen = () => {
      isConnected.value = true;
      currentConnectedGroupId.value = groupId.value;
      console.log(`WebSocket连接已建立，当前群组: ${groupId.value}`);

      // 清除之前的重连计时器
      clearReconnectTimer();
    };

    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('收到消息:', data);

        if (data.type === 'system_message') {
          // 系统消息
          messages.value.push({
            content: data.content,
            created_at: new Date().toISOString(),
            sender: { username: 'system' }
          });
        } else if (data.type === 'chat_message') {
          // 聊天消息
          messages.value.push(data.message);
        }

        // 滚动到底部
        scrollToBottom();
      } catch (e) {
        console.error('解析消息失败:', e);
      }
    };

    ws.value.onclose = (event) => {
      isConnected.value = false;
      console.log(`WebSocket连接已关闭: 代码=${event.code} 原因=${event.reason}`);

      // 如果不是主动关闭且应该重连，尝试重连
      if (shouldReconnect.value && event.code !== 1000) {
        console.log(`5秒后尝试重新连接群组 ${groupId.value}...`);

        // 清除之前的重连计时器
        clearReconnectTimer();

        // 设置新的重连计时器
        reconnectTimer.value = setTimeout(() => {
          if (currentConnectedGroupId.value !== groupId.value) {
            console.log(`群组已切换，不再重连到群组 ${groupId.value}`);
            return;
          }

          console.log(`重新连接到群组 ${groupId.value}`);
          connectWebSocket();
        }, 5000);
      }
    };

    ws.value.onerror = (error) => {
      console.error('WebSocket错误:', error);
      // WebSocket会在出错后自动关闭，触发onclose事件
    };
  }, 500); // 延迟500ms确保前一个连接已关闭
};

// ========== 导航和群组操作 ==========
// 返回群组列表
const goToGroups = () => {
  router.push('/groups');
};

// 切换群组
const switchGroup = (newGroupId) => {
  if (newGroupId !== parseInt(groupId.value)) {
    router.push(`/chat/${newGroupId}`);
    // 切换群组时关闭侧边栏
    if (isMobile.value) {
      closeAllSidebars();
    }
  }
};

// ========== 数据加载和初始化 ==========
// 加载群组数据
const loadGroupData = async () => {
  console.log(`加载群组 ${groupId.value} 数据`);

  // 清除之前的重连计时器
  clearReconnectTimer();

  // 先加载群组信息和消息
  const success = await fetchGroupInfoAndMessages();

  if (success) {
    // 再建立WebSocket连接
    connectWebSocket();
  }
};

// 刷新群组数据但不重连WebSocket
const refreshGroupData = async () => {
  try {
    // 刷新群组信息（包含成员列表）
    const groupResponse = await axios.get(`/api/groups/${groupId.value}`);
    groupInfo.value = groupResponse.data;
    groupMembers.value = groupResponse.data.members || [];
  } catch (error) {
    console.error('刷新群组数据失败:', error);
  }
};

// ========== 生命周期钩子 ==========
// 监听路由参数变化
watch(() => route.params.groupId, (newId) => {
  if (newId !== groupId.value) {
    console.log(`群组切换: ${groupId.value} -> ${newId}`);
    groupId.value = newId;

    // 取消之前的重连计时器
    clearReconnectTimer();

    // 当群组ID变化时，重新获取信息和建立连接
    loadGroupData();
  }
}, { immediate: true });

// 组件挂载
onMounted(async () => {
  try {
    console.log('Chat组件挂载，groupId:', groupId.value);

    // 添加窗口大小变化监听
    window.addEventListener('resize', updateWindowWidth);

    // 加载基础数据
    await Promise.all([
      fetchUserProfile(),
      fetchMyGroups()
    ]);

    // 加载群组数据并连接WebSocket
    await loadGroupData();
  } catch (error) {
    console.error('初始化聊天页面失败:', error);
    ElMessage.error('加载聊天页面失败');
  }
});

// 组件卸载
onBeforeUnmount(() => {
  console.log('聊天组件卸载中...');

  // 移除窗口大小变化监听
  window.removeEventListener('resize', updateWindowWidth);

  // 清除重连计时器
  clearReconnectTimer();

  // 关闭WebSocket连接
  if (ws.value) {
    shouldReconnect.value = false; // 设置为不重连
    console.log('关闭WebSocket连接');
    ws.value.close(1000, '用户离开页面');
    ws.value = null;
  }
});
</script>

<style scoped>
/* ========== 基础布局样式 ========== */
.chat-container {
  height: 100%;
  overflow: hidden;
  position: relative;
}

.full-height {
  height: 100%;
}

/* ========== 侧边栏遮罩层 ========== */
.sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1400;
}

/* ========== 左侧群组侧边栏样式 ========== */
.group-sidebar {
  background-color: #f7f8fc;
  border-right: 1px solid #e6e6e6;
  display: flex;
  flex-direction: column;
  transition: transform 0.3s ease;
}

.sidebar-header {
  padding: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e6e6e6;
}

.user-info {
  display: flex;
  align-items: center;
  flex: 1;
  overflow: hidden;
}

.user-name-container {
  margin-left: 10px;
  overflow: hidden;
}

.username {
  display: block;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.group-list {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
}

.group-list h3 {
  margin-top: 0;
  font-size: 1rem;
  color: #666;
  margin-bottom: 15px;
}

.no-groups {
  padding: 20px 0;
  text-align: center;
  color: #999;
}

/* 群组项样式 */
.group-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
  background-color: #eef1f6;
}

.group-item:hover {
  background-color: #dce2ee;
}

.group-item.active {
  background-color: #1976d2;
  color: white;
}

.group-id {
  font-size: 0.8rem;
  margin-right: 8px;
  color: inherit;
  opacity: 0.7;
}

.group-name {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ========== 中部聊天区域样式 ========== */
.chat-area {
  display: flex;
  flex-direction: column;
  padding: 0;
  flex: 1;
  overflow: hidden;
  position: relative;
  height: 100%;
  background-color: #f8f9fa;
}

/* 移动端导航栏 */
.mobile-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 15px;
  background-color: #ffffff;
  border-bottom: 1px solid #e6e6e6;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.chat-group-title {
  font-weight: bold;
  font-size: 16px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  text-align: center;
}

.message-wrapper {
  flex: 1;
  padding: 15px;
  overflow-y: auto;
}

.system-message {
  text-align: center;
  padding: 5px 15px;
  margin: 10px 0;
  color: #909399;
  font-size: 0.85rem;
}

/* 消息样式 */
.message {
  margin-bottom: 20px;
  display: flex;
}

.message-avatar {
  margin-right: 12px;
  flex-shrink: 0;
}

.message-username {
  font-size: 0.9rem;
  color: #606266;
  margin-bottom: 4px;
}

.message-content {
  display: flex;
  flex-direction: column;
  max-width: 70%;
}

.message-bubble {
  padding: 10px 15px;
  border-radius: 12px;
  position: relative;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.my-message {
  flex-direction: row-reverse;
}

.my-message .message-avatar {
  margin-right: 0;
  margin-left: 12px;
}

.my-message .message-content {
  align-items: flex-end;
}

.my-message .message-bubble {
  background-color: #ecf5ff;
  color: #409eff;
  border-radius: 12px 12px 0 12px;
}

.other-message .message-bubble {
  background-color: white;
  color: #303133;
  border-radius: 0 12px 12px 12px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.message-time {
  font-size: 0.7rem;
  color: #999;
  margin-top: 4px;
}

/* 图片消息样式 */
:deep(.message-bubble img) {
  max-width: 250px;
  max-height: 180px;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s;
  margin: 4px 0;
}

:deep(.message-bubble img:hover) {
  transform: scale(1.05);
}

/* iframe视频样式 */
:deep(.message-bubble iframe) {
  max-width: 100%;
  border-radius: 8px;
  margin: 8px 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 图片预览样式 */
.image-preview-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.preview-image {
  max-width: 90vw;
  max-height: 80vh;
  object-fit: contain;
  border-radius: 4px;
}

/* 输入区域样式 */
.chat-input-area {
  padding: 15px;
  background-color: white;
  border-top: 1px solid #e6e6e6;
}

/* 输入功能按钮区域 */
.input-actions {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.emoji-button {
  font-size: 16px;
}

/* 消息输入容器 */
.message-input-container {
  display: flex;
  gap: 10px;
}

.message-input {
  flex: 1;
}

.send-button {
  align-self: flex-end;
  height: 40px;
}

/* Emoji选择器样式 */
.emoji-picker {
  display: flex;
  flex-wrap: wrap;
  padding: 10px;
}

.emoji-item {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  cursor: pointer;
  transition: transform 0.1s;
}

.emoji-item:hover {
  transform: scale(1.2);
  background-color: #f5f7fa;
  border-radius: 4px;
}

/* 图片/视频URL输入弹出层样式 */
.image-url-input, .video-url-input {
  padding: 10px;
}

.popover-footer {
  margin-top: 10px;
  text-align: right;
}

/* ========== 右侧成员列表样式 ========== */
.members-list {
  background-color: #f7f8fc;
  border-left: 1px solid #e6e6e6;
  display: flex;
  flex-direction: column;
  transition: transform 0.3s ease;
}

.members-header {
  padding: 15px;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.members-header h3 {
  margin: 0;
  font-size: 1rem;
  color: #666;
}

.members-container {
  padding: 15px;
  flex: 1;
  overflow-y: auto;
}

.member-item {
  margin-bottom: 15px;
  display: flex;
  align-items: center;
}

.member-info {
  margin-left: 10px;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0; /* 允许内容缩小 */
}

.member-name {
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ========== 其他状态样式 ========== */
.empty-chat {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.no-members {
  padding: 20px 0;
  text-align: center;
  color: #999;
}

/* ========== 响应式样式 ========== */
/* 移动端侧边栏样式 */
@media screen and (max-width: 768px) {
  .group-sidebar, .members-list {
    position: fixed;
    top: 0;
    bottom: 0;
    width: 0 !important;
    z-index: 1500;
    max-width: 300px;
  }

  .group-sidebar {
    left: 0;
    transform: translateX(-100%); /* 默认隐藏 */
  }

  .members-list {
    right: 0;
    transform: translateX(100%); /* 默认隐藏 */
  }

  /* 显示时的样式 */
  .group-sidebar.mobile-visible {
    width: 80% !important;
    transform: translateX(0);
    box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
  }

  .members-list.mobile-visible {
    width: 80% !important;
    transform: translateX(0);
    box-shadow: -2px 0 10px rgba(0, 0, 0, 0.1);
  }
}

/* 平板设备样式 */
@media screen and (max-width: 992px) {
  .message-content {
    max-width: 80%;
  }

  :deep(.message-bubble img) {
    max-width: 200px;
    max-height: 150px;
  }
}

/* 移动设备样式 */
@media screen and (max-width: 768px) {
  .message-content {
    max-width: 85%;
  }

  .message-bubble {
    padding: 8px 12px;
  }

  :deep(.message-bubble img) {
    max-width: 180px;
    max-height: 120px;
  }

  .chat-input-area {
    padding: 10px;
  }

  .input-actions {
    margin-bottom: 8px;
    flex-wrap: wrap;
  }

  .message-input-container {
    gap: 8px;
  }

  .emoji-item {
    width: 30px;
    height: 30px;
  }
}

/* 小型移动设备 */
@media screen and (max-width: 480px) {
  .message-content {
    max-width: 90%;
  }

  :deep(.message-bubble img) {
    max-width: 160px;
    max-height: 100px;
  }

  :deep(.message-bubble iframe) {
    height: 200px;
  }

  .emoji-picker {
    padding: 5px;
  }

  .emoji-item {
    width: 28px;
    height: 28px;
    font-size: 18px;
  }
}
</style>