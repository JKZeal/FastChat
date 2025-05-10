<template>
  <div class="login-container">
    <el-card class="login-card animate__animated animate__fadeIn">
      <template #header>
        <div class="card-header">
          <h2>{{ isLogin ? '欢迎回来' : '创建新账号' }}</h2>
        </div>
      </template>
      <p class="app-title">FastChat - 即时通讯系统</p>

      <el-form :model="formData" ref="formRef" @submit.prevent="submitForm">
        <el-form-item prop="username" :rules="[{ required: true, message: '请输入用户名', trigger: 'blur' }]">
          <el-input v-model="formData.username" placeholder="用户名" clearable />
        </el-form-item>
        <el-form-item prop="password" :rules="[{ required: true, message: '请输入密码', trigger: 'blur' }]">
          <el-input v-model="formData.password" type="password" placeholder="密码" show-password clearable />
        </el-form-item>
        <el-form-item
          v-if="!isLogin"
          prop="confirmPassword"
          :rules="[
            { required: true, message: '请再次输入密码', trigger: 'blur' },
            { validator: validateConfirmPassword, trigger: 'blur' }
          ]"
        >
          <el-input v-model="formData.confirmPassword" type="password" placeholder="确认密码" show-password clearable />
        </el-form-item>

        <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" style="margin-bottom: 15px;" />

        <el-form-item>
          <el-button type="primary" @click="submitForm" :loading="loading" class="submit-button">
            {{ isLogin ? '登 录' : '注 册' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="toggle-link">
        <el-link type="primary" @click="toggleForm">
          {{ isLogin ? '没有账号？点击注册' : '已有账号？点击登录' }}
        </el-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { ElMessage } from 'element-plus';

const router = useRouter();
const isLogin = ref(true);
const loading = ref(false);
const errorMessage = ref('');
const formRef = ref(null); // Reference to the form for validation

const formData = reactive({
  username: '',
  password: '',
  confirmPassword: ''
});

// Validator for confirm password
const validateConfirmPassword = (rule, value, callback) => {
  if (!isLogin.value && value !== formData.password) {
    callback(new Error('两次输入的密码不一致!'));
  } else {
    callback();
  }
};

const resetFormFields = () => {
  formData.username = '';
  formData.password = '';
  formData.confirmPassword = ''; // Bug 2 Fix: Ensure confirmPassword is cleared
  errorMessage.value = '';
  if (formRef.value) {
    formRef.value.resetFields(); // Reset Element Plus form validation states
  }
};

const toggleForm = () => {
  isLogin.value = !isLogin.value;
  resetFormFields();
};

const submitForm = async () => {
  if (!formRef.value) return;

  formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      errorMessage.value = '';

      if (isLogin.value) {
        // Login logic
        try {
          const response = await axios.post('/api/token', {
            username: formData.username,
            password: formData.password
          });
          localStorage.setItem('token', response.data.access_token);
          localStorage.setItem('username', formData.username); // Storing username can be useful

          ElMessage.success('登录成功！');
          // Bug 1 Fix: Ensure navigation happens after token is set.
          // The router.beforeEach guard in router.js will handle redirection if already logged in.
          // Explicitly push to ensure the user is moved to the groups page.
          // If a "network error" still shows, it's likely from an initial data fetch
          // in the Group.vue component not being handled gracefully.
          await router.push('/groups');
        } catch (error) {
          if (error.response) {
            errorMessage.value = error.response.data.detail || '登录失败，用户名或密码错误。';
          } else if (error.request) {
            errorMessage.value = '网络连接错误，请检查您的网络并重试。';
          } else {
            errorMessage.value = '发生未知错误，请稍后重试。';
          }
          console.error("Login error:", error);
        }
      } else {
        // Registration logic
        // The confirmPassword check is now handled by the form validator
        try {
          await axios.post('/api/users/', {
            username: formData.username,
            password: formData.password
          });
          ElMessage.success('注册成功！请登录。');
          toggleForm(); // Switch to login form and clear fields
        } catch (error) {
          if (error.response) {
            // The backend correctly returns 400 for "用户名已被注册"
            errorMessage.value = error.response.data.detail || '注册失败，请重试。';
          } else if (error.request) {
            errorMessage.value = '网络连接错误，请检查您的网络并重试。';
          } else {
            errorMessage.value = '发生未知错误，请稍后重试。';
          }
          console.error("Registration error:", error);
        }
      }
      loading.value = false;
    } else {
      console.log('Form validation failed');
      return false;
    }
  });
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  /* background-color: #f0f2f5; */ /* Match your app's theme */
}

.login-card {
  width: 400px;
  max-width: 90%;
  padding: 20px;
}

.card-header h2 {
  text-align: center;
  margin: 0;
  /* color: #333; */ /* Match your app's theme */
}

.app-title {
  text-align: center;
  /* color: #555; */ /* Match your app's theme */
  margin-bottom: 20px;
  font-size: 1.1em;
}

.submit-button {
  width: 100%;
}

.toggle-link {
  margin-top: 15px;
  text-align: center;
}

/* Ensure inputs take full width if not already handled by Element Plus defaults */
.el-form-item .el-input {
  width: 100%;
}
</style>