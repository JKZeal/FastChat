<template>
  <div class="group-container">
    <!-- 三栏布局 -->
    <el-container class="full-height">
      <!-- 左侧: 个人资料区域 -->
      <el-aside width="250px" class="profile-sidebar">
        <div class="user-profile-card">
          <div class="avatar-container" @click="showAvatarSelector = true">
            <el-avatar :size="80" :src="userProfile.avatar_url || '/avatar/avatar0.png'"></el-avatar>
            <div class="avatar-edit-overlay">
              <el-icon><Edit /></el-icon>
            </div>
          </div>
          <h3>{{ userProfile.username }}</h3>

          <div class="bio-section" @click="showBioEditor = true">
            <p v-if="userProfile.bio" class="bio-text">{{ userProfile.bio }}</p>
            <p v-else class="no-bio">点击添加个人简介</p>
            <div class="bio-edit-overlay">
              <el-icon><Edit /></el-icon>
            </div>
          </div>
        </div>
      </el-aside>

      <!-- 中部: 我的群组 -->
      <el-main class="groups-main">
        <div class="section-header">
          <h2>我的群组</h2>
          <el-button type="primary" @click="showCreateGroupDialog = true" :icon="Plus">创建群组</el-button>
        </div>

        <div class="groups-list">
          <el-empty v-if="myGroups.length === 0" description="您还没有加入任何群组" />
          <el-card
            v-for="group in myGroups"
            :key="group.id"
            class="group-card"
            @click="enterChat(group.id)"
          >
            <div class="group-card-content">
              <div class="group-header">
                <div class="group-id">#{{ group.id }}</div>
                <h3>{{ group.name }}</h3>
              </div>
              <p class="group-description">{{ group.description || '没有描述' }}</p>
            </div>
          </el-card>
        </div>
      </el-main>

      <!-- 右侧: 发现群组 -->
      <el-aside width="300px" class="discover-sidebar">
        <div class="search-section">
          <h2>发现群组</h2>
          <el-input
            v-model="searchQuery"
            placeholder="搜索群组..."
            clearable
            @clear="clearSearch"
          >
            <template #suffix>
              <el-button :icon="Search" circle @click="searchGroups" :loading="isSearching"></el-button>
            </template>
          </el-input>
        </div>

        <div class="search-results">
          <el-empty
            v-if="searchQuery && searchAttempted && searchResults.length === 0"
            description="未找到匹配的群组"
          />
          <div v-else-if="!searchQuery && !searchAttempted" class="search-prompt">
            <el-icon><Search /></el-icon>
            <p>输入关键词搜索群组</p>
          </div>
          <!-- 简化的搜索结果卡片 -->
          <div
            v-else
            v-for="group in searchResults"
            :key="group.id"
            class="search-result-item"
          >
            <div class="search-result-header">
              <span class="search-result-id">#{{ group.id }}</span>
              <span class="search-result-name">{{ group.name }}</span>
            </div>
            <div class="search-result-actions">
              <el-button
                type="primary"
                size="small"
                @click.stop="joinGroup(group.id)"
                :disabled="isGroupJoined(group.id)"
              >
                {{ isGroupJoined(group.id) ? '已加入' : '加入' }}
              </el-button>
            </div>
          </div>
        </div>
      </el-aside>
    </el-container>

    <!-- 头像选择器弹窗 -->
    <el-dialog v-model="showAvatarSelector" title="选择头像" width="400px">
      <div class="avatar-grid">
        <div
          v-for="avatar in availableAvatars"
          :key="avatar"
          class="avatar-option"
          :class="{ 'avatar-selected': editableProfile.avatar_url === avatar }"
          @click="selectAvatar(avatar)"
        >
          <el-avatar :src="avatar" :size="50"></el-avatar>
        </div>
      </div>
      <template #footer>
        <el-button @click="showAvatarSelector = false">取消</el-button>
        <el-button type="primary" @click="saveAvatar">确认</el-button>
      </template>
    </el-dialog>

    <!-- 个人简介编辑器弹窗 -->
    <el-dialog v-model="showBioEditor" title="编辑个人简介" width="400px">
      <el-input
        v-model="editableProfile.bio"
        type="textarea"
        placeholder="写一些关于你自己的内容..."
        :rows="5"
        :autosize="{ minRows: 3, maxRows: 8 }"
        maxlength="200"
        show-word-limit
        class="bio-textarea"
      ></el-input>
      <template #footer>
        <el-button @click="showBioEditor = false">取消</el-button>
        <el-button type="primary" @click="saveBio">保存</el-button>
      </template>
    </el-dialog>

    <!-- 创建群组对话框 -->
    <el-dialog v-model="showCreateGroupDialog" title="创建新群组" width="500px">
      <el-form
        :model="newGroup"
        label-position="top"
        :rules="groupFormRules"
        ref="createGroupFormRef"
      >
        <el-form-item label="群组名称" prop="name">
          <el-input v-model="newGroup.name" placeholder="输入群组名称"></el-input>
        </el-form-item>
        <el-form-item label="群组描述" prop="description">
          <el-input
            v-model="newGroup.description"
            type="textarea"
            placeholder="描述这个群组的用途..."
            :rows="3"
            maxlength="500"
            show-word-limit
          ></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateGroupDialog = false">取消</el-button>
        <el-button type="primary" @click="createGroup">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { ElMessage } from 'element-plus';
import { Plus, Search, Edit } from '@element-plus/icons-vue';

const router = useRouter();
const availableAvatars = ref([]);

// 移除状态相关的字段
const userProfile = ref({
  username: '',
  avatar_url: '',
  bio: ''
});

const editableProfile = reactive({
  username: '',
  avatar_url: '',
  bio: ''
});

const myGroups = ref([]);
const searchResults = ref([]);
const searchQuery = ref('');
const isSearching = ref(false);
const searchAttempted = ref(false);

const showAvatarSelector = ref(false);
const showBioEditor = ref(false);
const showCreateGroupDialog = ref(false);
const createGroupFormRef = ref(null);

const newGroup = reactive({
  name: '',
  description: ''
});

// 表单验证规则
const groupFormRules = {
  name: [
    { required: true, message: '请输入群组名称', trigger: 'blur' },
    { min: 2, max: 30, message: '长度应为2到30个字符', trigger: 'blur' },
    { validator: validateGroupName, trigger: 'blur' }
  ],
  description: [
    { max: 500, message: '描述不能超过500个字符', trigger: 'blur' }
  ]
};

// 验证群组名是否已存在
async function validateGroupName(rule, value, callback) {
  if (!value) {
    callback();
    return;
  }

  try {
    // 检查是否有同名群组
    const response = await axios.get('/api/groups/search', {
      params: { name: value }
    });

    const existingGroups = response.data;
    const exactMatch = existingGroups.find(group =>
      group.name.toLowerCase() === value.toLowerCase()
    );

    if (exactMatch) {
      callback(new Error('群组名已存在，请使用其他名称'));
    } else {
      callback();
    }
  } catch (error) {
    console.error('验证群组名时出错:', error);
    // 验证出错时，允许表单继续提交，后端会进行二次验证
    callback();
  }
}

// 检查群组是否已加入
const isGroupJoined = (groupId) => {
  return myGroups.value.some(group => group.id === groupId);
};

// 动态获取所有可用头像
const fetchAvailableAvatars = async () => {
  try {
    // 使用API端点获取所有头像
    const response = await axios.get('/api/avatar/list');
    if (response.data && Array.isArray(response.data)) {
      availableAvatars.value = response.data;
    } else {
      // 如果API未返回有效数据，设置一些默认头像
      availableAvatars.value = [
        '/avatar/avatar0.png',
        '/avatar/avatar1.png',
        '/avatar/avatar2.png',
        '/avatar/avatar3.png',
        '/avatar/avatar4.png',
      ];
    }
  } catch (error) {
    console.error('获取头像列表失败:', error);
    // 设置默认头像列表
    availableAvatars.value = [
      '/avatar/avatar0.png',
      '/avatar/avatar1.png',
      '/avatar/avatar2.png',
      '/avatar/avatar3.png',
      '/avatar/avatar4.png',
    ];
  }
};

// API 请求方法
const fetchUserProfile = async () => {
  try {
    const response = await axios.get('/api/users/me/');
    userProfile.value = response.data;

    // 将用户资料复制到可编辑对象
    editableProfile.username = userProfile.value.username;
    editableProfile.avatar_url = userProfile.value.avatar_url;
    editableProfile.bio = userProfile.value.bio;
  } catch (error) {
    console.error('获取用户信息失败:', error);
    if (error.response && error.response.status === 401) {
      router.push('/login');
    }
  }
};

const fetchMyGroups = async () => {
  try {
    const response = await axios.get('/api/groups/');
    myGroups.value = response.data;
  } catch (error) {
    console.error('获取群组列表失败:', error);
  }
};

const selectAvatar = (avatar) => {
  editableProfile.avatar_url = avatar;
};

// 保存头像
const saveAvatar = async () => {
  try {
    const response = await axios.put('/api/users/me/profile', {
      avatar_url: editableProfile.avatar_url,
      bio: userProfile.value.bio
    });
    userProfile.value = response.data;
    showAvatarSelector.value = false;
    ElMessage.success('头像已更新');
  } catch (error) {
    console.error('更新头像失败:', error);
    ElMessage.error('更新头像失败');
  }
};

// 保存个人简介
const saveBio = async () => {
  try {
    const response = await axios.put('/api/users/me/profile', {
      avatar_url: userProfile.value.avatar_url,
      bio: editableProfile.bio
    });
    userProfile.value = response.data;
    showBioEditor.value = false;
    ElMessage.success('个人简介已更新');
  } catch (error) {
    console.error('更新个人简介失败:', error);
    ElMessage.error('更新个人简介失败');
  }
};

const createGroup = async () => {
  if (!createGroupFormRef.value) return;

  await createGroupFormRef.value.validate(async (valid) => {
    if (!valid) return;

    try {
      // 再次检查是否存在同名群组
      const checkResponse = await axios.get('/api/groups/search', {
        params: { name: newGroup.name }
      });

      const existingGroups = checkResponse.data;
      const exactMatch = existingGroups.find(group =>
        group.name.toLowerCase() === newGroup.name.toLowerCase()
      );

      if (exactMatch) {
        ElMessage.error('群组名已存在，请使用其他名称');
        return;
      }

      const response = await axios.post('/api/groups/', newGroup);
      myGroups.value.push(response.data);
      newGroup.name = '';
      newGroup.description = '';
      showCreateGroupDialog.value = false;
      ElMessage.success('群组创建成功');
    } catch (error) {
      console.error('创建群组失败:', error);
      ElMessage.error('创建群组失败');
    }
  });
};

const searchGroups = async () => {
  if (!searchQuery.value.trim()) {
    searchResults.value = [];
    searchAttempted.value = false;
    return;
  }

  isSearching.value = true;
  try {
    // 使用name参数搜索群组
    const response = await axios.get('/api/groups/search', {
      params: { name: searchQuery.value }
    });
    searchResults.value = response.data;
    searchAttempted.value = true;
    console.log('搜索结果:', searchResults.value);
  } catch (error) {
    console.error('搜索群组失败:', error);
    ElMessage.error('搜索群组失败');
  } finally {
    isSearching.value = false;
  }
};

const clearSearch = () => {
  searchResults.value = [];
  searchQuery.value = '';
  searchAttempted.value = false;
};

const joinGroup = async (groupId) => {
  try {
    await axios.post(`/api/groups/${groupId}/join`);
    ElMessage.success('已成功加入群组');

    // 刷新我的群组列表
    await fetchMyGroups();

    // 重新渲染搜索结果
    searchResults.value = [...searchResults.value];
  } catch (error) {
    console.error('加入群组失败:', error);
    ElMessage.error('加入群组失败');
  }
};

const enterChat = (groupId) => {
  router.push(`/chat/${groupId}`);
};

// 页面可见性处理
const handleVisibilityChange = () => {
  if (document.visibilityState === 'hidden') {
    console.log('页面不可见');
  } else {
    console.log('页面可见');
    fetchUserProfile();
  }
};

// 生命周期钩子
onMounted(() => {
  document.addEventListener('visibilitychange', handleVisibilityChange);

  // 移除beforeunload事件中的logout请求

  // 初始化数据获取
  fetchAvailableAvatars();
  fetchUserProfile();
  fetchMyGroups();
});

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange);
});
</script>

<style scoped>
.group-container {
  height: 100%;
  width: 100%;
  overflow: hidden;
}

.full-height {
  height: 100%;
}

/* 左侧个人资料栏 */
.profile-sidebar {
  background-color: #f9f9f9;
  border-right: 1px solid #e4e4e4;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.user-profile-card {
  text-align: center;
  padding: 20px 0;
}

.avatar-container {
  margin-bottom: 15px;
  position: relative;
  display: inline-block;
  cursor: pointer;
}

.avatar-edit-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 50%;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  opacity: 0;
  transition: opacity 0.2s;
  color: white;
}

.avatar-container:hover .avatar-edit-overlay {
  opacity: 1;
}

.bio-section {
  margin: 15px 0;
  padding: 10px;
  border-radius: 8px;
  position: relative;
  cursor: pointer;
  transition: background-color 0.2s;
  max-width: 100%;
}

.bio-section:hover {
  background-color: #f0f0f0;
}

.bio-text {
  word-break: break-word;
  white-space: pre-wrap;
  max-width: 100%;
  overflow-wrap: break-word;
  margin: 0;
}

.bio-edit-overlay {
  position: absolute;
  top: 5px;
  right: 5px;
  opacity: 0;
  transition: opacity 0.2s;
}

.bio-section:hover .bio-edit-overlay {
  opacity: 0.7;
}

.no-bio {
  color: #999;
  font-style: italic;
  margin: 0;
}

/* 中部群组列表 */
.groups-main {
  padding: 20px;
  overflow-y: auto;
  background-color: #fff;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.groups-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 20px;
}

/* 群组卡片样式 - 简化版 */
.group-card {
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border-radius: 8px;
  overflow: hidden;
}

.group-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0,0,0,0.1);
}

.group-card-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.group-header {
  background-color: #4c84ff;
  color: white;
  padding: 12px 15px;
  position: relative;
}

.group-id {
  position: absolute;
  top: 8px;
  right: 10px;
  background: rgba(255,255,255,0.3);
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 0.8rem;
}

.group-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.group-description {
  padding: 12px 15px;
  color: #555;
  margin: 0;
  font-size: 0.9rem;
  background-color: white;
  flex-grow: 1;
  word-break: break-word;
  overflow-wrap: break-word;
  white-space: pre-wrap;
}

/* 右侧发现栏 */
.discover-sidebar {
  background-color: #f9f9f9;
  border-left: 1px solid #e4e4e4;
  padding: 20px;
  overflow-y: auto;
}

.search-section {
  margin-bottom: 20px;
}

.search-results {
  margin-top: 20px;
}

.search-prompt {
  text-align: center;
  color: #999;
  margin-top: 50px;
}

.search-prompt .el-icon {
  font-size: 24px;
  margin-bottom: 10px;
}

/* 搜索结果项 - 简洁版 */
.search-result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background-color: white;
  border-radius: 8px;
  margin-bottom: 10px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}

.search-result-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-result-id {
  color: #999;
  font-size: 0.85rem;
}

.search-result-name {
  font-weight: bold;
}

/* 头像选择 */
.bio-textarea {
  width: 100%;
}

.avatar-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  margin-top: 10px;
}

.avatar-option {
  cursor: pointer;
  padding: 5px;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 50%;
}

.avatar-option:hover {
  background-color: #f0f0f0;
}

.avatar-selected {
  background-color: #ecf5ff;
}

.el-textarea__inner {
  resize: none;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>