<template>
  <div class="login-page-wrapper">
    <div class="login-container">
      <!-- 登录表单 -->
      <template v-if="!isRegistering">
        <h2>排课系统登录</h2>
        <form @submit.prevent="handleLogin">
          <div class="form-group">
            <label for="username">用户名:</label>
            <input type="text" id="username" v-model="username" required>
          </div>
          <div class="form-group">
            <label for="password">密码:</label>
            <input type="password" id="password" v-model="password" required>
          </div>
          <div class="form-group">
            <label for="user-type">用户类型:</label>
            <select id="user-type" v-model="userType" required>
              <option value="student">学生</option>
              <option value="teacher">教师</option>
              <option value="admin">管理员</option>
            </select>
          </div>
          <button type="submit">登录</button>
        </form>
        <p class="switch-link">
          还没有账号？ <a href="#" @click.prevent="toggleRegistering(true)">立即注册</a>
        </p>
      </template>

      <!-- 注册表单 -->
      <template v-else>
        <h2>用户注册</h2>
        <form @submit.prevent="handleRegister">
          <div class="form-group">
            <label for="reg-username">用户名:</label>
            <input type="text" id="reg-username" v-model="regUsername" required>
          </div>
          <div class="form-group">
            <label for="reg-password">密码:</label>
            <input type="password" id="reg-password" v-model="regPassword" required>
          </div>
          <div class="form-group">
            <label for="reg-confirm-password">确认密码:</label>
            <input type="password" id="reg-confirm-password" v-model="regConfirmPassword" required>
          </div>
          <div class="form-group">
            <label for="reg-user-type">用户类型:</label>
            <select id="reg-user-type" v-model="regUserType" required>
              <option value="student">学生</option>
              <option value="teacher">教师</option>
              <option value="admin">管理员</option>
            </select>
          </div>
          <button type="submit">注册</button>
        </form>
        <p class="switch-link">
          已有账号？ <a href="#" @click.prevent="toggleRegistering(false)">返回登录</a>
        </p>
      </template>

      <p v-if="successMessage" class="message success">{{ successMessage }}</p>
      <p v-if="errorMessage" class="message error">{{ errorMessage }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios'; // 导入 axios

// 登录表单数据
const username = ref('');
const password = ref('');
const userType = ref('student');

// 注册表单数据
const isRegistering = ref(false); // 控制显示登录还是注册表单
const regUsername = ref('');
const regPassword = ref('');
const regConfirmPassword = ref('');
const regUserType = ref('student');

// 消息
const errorMessage = ref('');
const successMessage = ref('');

const router = useRouter();

// 后端 API 基础 URL
const API_BASE_URL = 'http://localhost:5000'; // 确保与 Flask 后端运行的地址和端口一致

// 切换登录/注册表单
const toggleRegistering = (value) => {
  isRegistering.value = value;
  errorMessage.value = ''; // 清空错误信息
  successMessage.value = ''; // 清空成功信息
  // 切换时清空对应表单数据 (可选)
  if (value) { // 切换到注册
    username.value = '';
    password.value = '';
    userType.value = 'student';
  } else { // 切换到登录
    regUsername.value = '';
    regPassword.value = '';
    regConfirmPassword.value = '';
    regUserType.value = 'student';
  }
};

const handleLogin = async () => {
  errorMessage.value = '';
  successMessage.value = '';

  try {
    const response = await axios.post(`${API_BASE_URL}/login`, {
      username: username.value,
      password: password.value,
      userType: userType.value,
    });

    console.log('Login successful:', response.data);

    // 假设后端返回 token 和 user_role
    localStorage.setItem('token', response.data.token);
    localStorage.setItem('userRole', response.data.user_role);
    localStorage.setItem('username', username.value); // 存储用户名
    localStorage.setItem('user_id', response.data.user_id);
    // 根据后端返回的角色进行跳转
    if (response.data.user_role === 'admin') {
      router.push('/admin');
    } else if (response.data.user_role === 'teacher') {
      router.push('/teacher');
    } else if (response.data.user_role === 'student') {
      router.push('/student');
    } else {
      errorMessage.value = '后端返回未知用户角色。';
    }

  } catch (error) {
    console.error('Login error:', error.response?.data || error.message);
    errorMessage.value = error.response?.data?.message || '登录失败，请检查用户名、密码或用户类型。';
  }
};

const handleRegister = async () => {
  errorMessage.value = '';
  successMessage.value = '';

  if (regPassword.value !== regConfirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致！';
    return;
  }

  try {
    const response = await axios.post(`${API_BASE_URL}/register`, {
      username: regUsername.value,
      password: regPassword.value,
      userType: regUserType.value,
    });

    console.log('Registration successful:', response.data);
    successMessage.value = '注册成功！请返回登录页面。';
    // 注册成功后，可以自动切换回登录页面，并填充用户名 (可选)
    // username.value = regUsername.value;
    // password.value = ''; // 清空密码
    // userType.value = regUserType.value;
    // isRegistering.value = false;
    // 清空注册表单
    regUsername.value = '';
    regPassword.value = '';
    regConfirmPassword.value = '';
    regUserType.value = 'student';

  } catch (error) {
    console.error('Registration error:', error.response?.data || error.message);
    errorMessage.value = error.response?.data?.message || '注册失败，请稍后重试。';
  }
};
</script>

<style scoped>
/* 保持您原有的样式，并添加一些注册相关的样式 */

.login-page-wrapper {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height:100vh;
    width: 100vw; /* 确保宽度覆盖整个视口 */
    background-image: url('https://www.nudt.edu.cn/skd/images/2023-08/e025ebeb00774757b3a4a6d523aec503jpg');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}

.login-container {
  background-color: rgba(255, 255, 255, 0.9);
  width: 400px;
  padding: 30px;
  border: 1px solid #ccc;
  border-radius: 8px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
  z-index: 1;
}
h2 {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
}
.form-group {
  margin-bottom: 20px;
}
label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
  color: #555;
}
input[type="text"],
input[type="password"],
select {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
  font-size: 16px;
}
button {
  width: 100%;
  margin-top:20px;
  padding: 12px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 18px;
  transition: background-color 0.3s ease;
}
button:hover {
  background-color: #0056b3;
}
.message { /* 统一错误和成功消息的样式 */
  text-align: center;
  margin-top: 15px;
  font-size: 14px;
  padding: 10px;
  border-radius: 4px;
}
.message.error {
  color: #a94442;
  background-color: #f2dede;
  border: 1px solid #ebccd1;
}
.message.success {
  color: #3c763d;
  background-color: #dff0d8;
  border: 1px solid #d6e9c6;
}

.switch-link {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: #666;
}
.switch-link a {
  color: #007bff;
  text-decoration: none;
  font-weight: bold;
}
.switch-link a:hover {
  text-decoration: underline;
}
</style>
