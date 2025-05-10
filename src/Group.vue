<template>
  <el-container class="group-container">
    <!-- Header -->
    <el-header class="group-header">
      <div class="user-profile-summary">
        <el-avatar :size="40" :src="userProfile.avatar_url || undefined" @click="showProfileDialog = true">
          {{ userProfile.username?.charAt(0).toUpperCase() }}
        </el-avatar>
        <div class="user-info" @click="showProfileDialog = true">
          <span class="username">{{ userProfile.username || '用户' }}</span>
          <span class="status">{{ userProfile.status || '在线' }}</span>
        </div>
      </div>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="showCreateGroupDialog = true">创建群组</el-button>
        <el-button type="danger" :icon="SwitchButton" @click="logout">退出登录</el-button>
      </div>
    </el-header>

    <!-- Main Content -->
    <el-main class="group-main">
      <el-tabs v-model="activeTab">
        <!-- My Groups Tab -->
        <el-tab-pane label="我的群组" name="myGroups">
          <el-row :gutter="20" v-if="myGroups.length > 0">
            <el-col :span="8" v-for="group in myGroups" :key="group.id" class="group-card-col">
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>{{ group.name }}</span>
                    <el-dropdown @command="(command) => handleGroupCommand(command, group)">
                      <el-button :icon="MoreFilled" circle text size="small"></el-button>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item command="leave" :icon="Remove">退出群组</el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </div>
                </template>
                <p class="group-description">{{ group.description || '暂无描述' }}</p>
                <div class="group-meta">创建于: {{ new Date(group.created_at).toLocaleDateString() }}</div>
                <el-button type="primary" plain @click="goToChat(group)" class="full-width-button">进入聊天</el-button>
              </el-card>
            </el-col>
          </el-row>
          <el-empty v-else description="您还没有加入任何群组，快去发现或创建一个吧！"></el-empty>
        </el-tab-pane>

        <!-- Discover Groups Tab -->
        <el-tab-pane label="发现群组" name="discoverGroups">
          <el-input v-model="searchQuery" placeholder="按名称或ID搜索群组" clearable @clear="clearSearch" class="search-input">
            <template #append>
              <el-button :icon="Search" @click="searchGroups"></el-button>
            </template>
          </el-input>
          <div v-if="isSearching" class="loading-search"><el-icon class="is-loading"><Loading /></el-icon> 正在搜索...</div>

          <div v-if="searchResults.length > 0" class="search-results">
            <h4>搜索结果：</h4>
            <el-row :gutter="20">
               <el-col :span="8" v-for="group in searchResults" :key="group.id" class="group-card-col">
                <el-card shadow="hover">
                   <template #header><span>{{ group.name }}</span></template>
                  <p class="group-description">{{ group.description || '无描述' }}</p>
                  <el-button type="success" @click="joinGroup(group.id)" class="full-width-button" :disabled="isMemberOf(group.id)">
                    {{ isMemberOf(group.id) ? '已加入' : '加入群组' }}
                  </el-button>
                </el-card>
              </el-col>
            </el-row>
          </div>
          <el-empty v-else-if="!isSearching && searchAttempted" description="未找到相关群组"></el-empty>
        </el-tab-pane>
      </el-tabs>
    </el-main>

    <!-- Dialog for User Profile -->
    <el-dialog v-model="showProfileDialog" title="编辑个人资料" width="400px">
      <el-form :model="editableProfile" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="editableProfile.username" disabled></el-input>
        </el-form-item>
        <el-form-item label="状态">
          <el-input v-model="editableProfile.status" placeholder="如：在线、忙碌"></el-input>
        </el-form-item>
        <el-form-item label="简介">
          <el-input type="textarea" v-model="editableProfile.bio" placeholder="介绍一下自己吧"></el-input>
        </el-form-item>
        <el-form-item label="头像">
          <el-upload
            action="#"
            :before-upload="handleAvatarUpload"
            :show-file-list="false"
            accept="image/png, image/jpeg, image/gif, image/webp"
          >
            <el-button :icon="Upload">选择图片</el-button>
          </el-upload>
          <el-avatar v-if="avatarPreviewUrl || editableProfile.avatar_url" :src="avatarPreviewUrl || editableProfile.avatar_url" :size="60" style="margin-left: 10px;"></el-avatar>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showProfileDialog = false">取消</el-button>
        <el-button type="primary" @click="updateProfile">保存</el-button>
      </template>
    </el-dialog>

    <!-- Dialog for Create Group -->
    <el-dialog v-model="showCreateGroupDialog" title="创建新群组" width="400px">
      <el-form :model="newGroup" label-width="80px" ref="createGroupFormRef">
        <el-form-item label="群组名称" prop="name" :rules="[{ required: true, message: '请输入群组名称', trigger: 'blur' }]">
          <el-input v-model="newGroup.name"></el-input>
        </el-form-item>
        <el-form-item label="群组描述" prop="description">
          <el-input type="textarea" v-model="newGroup.description"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateGroupDialog = false">取消</el-button>
        <el-button type="primary" @click="createGroup">创建</el-button>
      </template>
    </el-dialog>

    <!-- Dialog for Leave Group Confirmation -->
    <el-dialog v-model="showLeaveConfirmDialog" title="确认退出" width="350px">
      <span>确定要退出群组 "<strong>{{ groupToLeave?.name }}</strong>" 吗？</span>
      <template #footer>
        <el-button @click="showLeaveConfirmDialog = false">取消</el-button>
        <el-button type="danger" @click="confirmLeaveGroup">退出群组</el-button>
      </template>
    </el-dialog>

  </el-container>
</template>

<script setup>
import { ref, onMounted, reactive, computed } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, SwitchButton, Search, MoreFilled, Remove, Upload, Loading } from '@element-plus/icons-vue';

const router = useRouter();

const userProfile = ref({
  username: localStorage.getItem('username') || '',
  avatar_url: '',
  status: '',
  bio: ''
});
const editableProfile = reactive({ username: '', avatar_url: '', status: '', bio: '' });
const avatarFile = ref(null);
const avatarPreviewUrl = ref('');

const myGroups = ref([]);
const searchResults = ref([]);
const searchQuery = ref('');
const isSearching = ref(false);
const searchAttempted = ref(false); // To show "not found" only after a search

const newGroup = reactive({ name: '', description: '' });
const createGroupFormRef = ref(null);

const showProfileDialog = ref(false);
const showCreateGroupDialog = ref(false);
const showLeaveConfirmDialog = ref(false);
const groupToLeave = ref(null);

const activeTab = ref('myGroups');

const fetchUserProfile = async () => {
  try {
    const response = await axios.get('/api/users/me/');
    userProfile.value = response.data;
    // Initialize editableProfile when userProfile is fetched
    Object.assign(editableProfile, JSON.parse(JSON.stringify(response.data)));
  } catch (error) {
    console.error('获取用户信息失败:', error);
    ElMessage.error('获取用户信息失败，请重试。');
  }
};

const fetchMyGroups = async () => {
  try {
    const response = await axios.get('/api/groups/');
    myGroups.value = response.data;
  } catch (error) {
    console.error('获取我的群组失败:', error);
    ElMessage.error('获取我的群组列表失败。');
  }
};

const handleAvatarUpload = (file) => {
  const isImage = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(file.type);
  const isLt2M = file.size / 1024 / 1024 < 2;

  if (!isImage) {
    ElMessage.error('上传头像图片只能是 JPG/PNG/GIF/WEBP 格式!');
    return false;
  }
  if (!isLt2M) {
    ElMessage.error('上传头像图片大小不能超过 2MB!');
    return false;
  }
  avatarFile.value = file;
  avatarPreviewUrl.value = URL.createObjectURL(file); // Create a preview URL
  return false; // Prevent el-upload's default upload
};

const updateProfile = async () => {
  const formData = new FormData();
  if (editableProfile.status !== userProfile.value.status) {
    formData.append('status', editableProfile.status);
  }
  if (editableProfile.bio !== userProfile.value.bio) {
    formData.append('bio', editableProfile.bio);
  }
  if (avatarFile.value) {
    formData.append('avatar', avatarFile.value);
  }

  // Check if there's anything to update
  let hasChanges = false;
  for (const _ of formData.entries()) { // formData.entries() is an iterator
      hasChanges = true;
      break;
  }
  if (!hasChanges) {
      ElMessage.info('个人资料未作更改。');
      showProfileDialog.value = false;
      return;
  }


  try {
    const response = await axios.put('/api/users/me/profile', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    userProfile.value = response.data; // Update local profile
    Object.assign(editableProfile, JSON.parse(JSON.stringify(response.data))); // Sync editable
    avatarFile.value = null; // Reset avatar file
    avatarPreviewUrl.value = ''; // Reset preview
    ElMessage.success('个人资料更新成功！');
    showProfileDialog.value = false;
  } catch (error) {
    console.error('更新个人资料失败:', error);
    ElMessage.error('更新个人资料失败: ' + (error.response?.data?.detail || error.message));
  }
};


const createGroup = async () => {
  if (!createGroupFormRef.value) return;
  createGroupFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const response = await axios.post('/api/groups/', newGroup);
        myGroups.value.push(response.data);
        ElMessage.success(`群组 "${response.data.name}" 创建成功！`);
        showCreateGroupDialog.value = false;
        newGroup.name = '';
        newGroup.description = '';
        activeTab.value = 'myGroups'; // Switch to my groups
      } catch (error) {
        console.error('创建群组失败:', error);
        ElMessage.error('创建群组失败: ' + (error.response?.data?.detail || error.message));
      }
    } else {
      return false;
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
  searchAttempted.value = true;
  try {
    // Determine if search is by ID or name
    const params = {};
    if (/^\d+$/.test(searchQuery.value)) { // If it's a number, search by ID
        params.id = parseInt(searchQuery.value);
    } else { // Otherwise, search by name
        params.name = searchQuery.value;
    }
    const response = await axios.get('/api/groups/search', { params });
    searchResults.value = response.data;
  } catch (error) {
    console.error('搜索群组失败:', error);
    ElMessage.error('搜索群组失败。');
    searchResults.value = [];
  } finally {
    isSearching.value = false;
  }
};

const clearSearch = () => {
  searchQuery.value = '';
  searchResults.value = [];
  searchAttempted.value = false;
};

const joinGroup = async (groupId) => {
  try {
    const response = await axios.post(`/api/groups/${groupId}/join`);
    ElMessage.success(`成功加入群组 "${response.data.name}"！`);
    // Add to myGroups if not already there (response.data is the group detail)
    if (!myGroups.value.find(g => g.id === response.data.id)) {
        myGroups.value.push(response.data);
    }
    // Optionally, refresh myGroups or update searchResults status
    await fetchMyGroups(); // Refresh the list of my groups
    // Update the specific group in searchResults to reflect joined status, if needed
    const searchedGroup = searchResults.value.find(g => g.id === groupId);
    if (searchedGroup) {
        // This is tricky as searchResults doesn't have member status.
        // isMemberOf will handle the button state.
    }

  } catch (error) {
    console.error('加入群组失败:', error);
    ElMessage.error('加入群组失败: ' + (error.response?.data?.detail || error.message));
  }
};

const isMemberOf = (groupId) => {
    return myGroups.value.some(g => g.id === groupId);
};

const handleGroupCommand = (command, group) => {
  if (command === 'leave') {
    groupToLeave.value = group;
    showLeaveConfirmDialog.value = true;
  }
};

const confirmLeaveGroup = async () => {
  if (!groupToLeave.value) return;
  try {
    await axios.post(`/api/groups/${groupToLeave.value.id}/leave`);
    ElMessage.success(`已成功退出群组 "${groupToLeave.value.name}"`);
    myGroups.value = myGroups.value.filter(g => g.id !== groupToLeave.value.id);
    showLeaveConfirmDialog.value = false;
    groupToLeave.value = null;
  } catch (error) {
    console.error('退出群组失败:', error);
    ElMessage.error('退出群组失败: ' + (error.response?.data?.detail || error.message));
  }
};

const goToChat = (group) => {
  if (group && group.id !== undefined && group.id !== null) {
    console.log(`Navigating to chat for group ID: ${group.id} (type: ${typeof group.id})`);
    router.push(`/chat/${group.id}`);
  } else {
    console.error('goToChat: Invalid group or group ID:', group);
    ElMessage.error('无法进入聊天室：群组信息无效。');
  }
};

const logout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('username');
  router.push('/login');
  ElMessage.success('已成功退出登录。');
};

onMounted(() => {
  fetchUserProfile();
  fetchMyGroups();
});
</script>

<style scoped>
.group-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  border-bottom: 1px solid var(--el-border-color-light);
  background-color: #f5f7fa;
  height: 60px;
  flex-shrink: 0;
}

.user-profile-summary {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.user-info {
  margin-left: 10px;
  display: flex;
  flex-direction: column;
}

.user-info .username {
  font-weight: bold;
}

.user-info .status {
  font-size: 0.8em;
  color: #606266;
}

.header-actions .el-button {
  margin-left: 10px;
}

.group-main {
  padding: 20px;
  overflow-y: auto; /* Allow main content to scroll if needed */
  flex-grow: 1;
}

.group-card-col {
  margin-bottom: 20px;
}

.el-card {
  height: 100%; /* Make cards in a row same height */
  display: flex;
  flex-direction: column;
}
.el-card :deep(.el-card__body) {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}


.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-header span {
  font-weight: bold;
}

.group-description {
  font-size: 0.9em;
  color: #606266;
  margin-bottom: 10px;
  flex-grow: 1; /* Allow description to take space */
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3; /* Limit to 3 lines */
  -webkit-box-orient: vertical;
}
.group-meta {
    font-size: 0.8em;
    color: #909399;
    margin-bottom: 10px;
}


.full-width-button {
  width: 100%;
  margin-top: auto; /* Push button to bottom */
}

.search-input {
  margin-bottom: 20px;
}
.loading-search {
  text-align: center;
  color: #909399;
  margin-bottom: 20px;
}
.search-results h4 {
  margin-bottom: 10px;
}

/* Ensure el-upload button looks like other buttons */
.el-form-item .el-upload {
  display: inline-block; /* Or block, depending on layout */
}
</style>