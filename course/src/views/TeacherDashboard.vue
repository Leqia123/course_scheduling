<template>
  <el-container class="teacher-dashboard-layout">
    <el-aside width="250px" class="sidebar">
      <div class="sidebar-content">
        <h2 class="sidebar-title">教师功能</h2>
        <el-menu
          :default-active="activeMenu"
          class="el-menu-vertical-teacher"
          router
          background-color="#343a40"
          text-color="#ffffff"
          active-text-color="#ffd04b"
        >
          <el-menu-item index="/teacher/timetable">
            <el-icon><Calendar /></el-icon>
            <span>查询课表</span>
          </el-menu-item>
          <el-menu-item index="/teacher/scheduling-request">
            <el-icon><MessageBox /></el-icon> <!-- Or EditPen -->
            <span>提出排课要求</span>
          </el-menu-item>
          <!-- Add more menu items here if needed -->
        </el-menu>

        <div class="user-info">
          <p>欢迎您，{{ loggedInUsername }}！</p>
          <el-button type="danger" @click="logout" class="logout-button" plain>
            退出登录
          </el-button>
        </div>
      </div>
    </el-aside>

    <el-main class="main-content">
      <!-- Content area -->
      <router-view v-slot="{ Component }">
        <transition name="fade-transform" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import {
  ElContainer, ElAside, ElMain, ElMenu, ElMenuItem, ElButton, ElIcon
} from 'element-plus';
// Import desired icons (ensure @element-plus/icons-vue is installed)
import { Calendar, MessageBox, EditPen } from '@element-plus/icons-vue'; // Choose appropriate icons

const router = useRouter();
const route = useRoute(); // Get current route information
const loggedInUsername = ref('');

onMounted(() => {
  loggedInUsername.value = localStorage.getItem('username') || '教师用户';
});

// Calculate the active menu item based on the current route
const activeMenu = computed(() => {
  const { path } = route;
  return path;
});

const logout = () => {
  // Clear user login status and username
  localStorage.removeItem('token');
  localStorage.removeItem('userRole');
  localStorage.removeItem('username');
  router.push('/login'); // Redirect to login page
  // Optional: Show a success message
  // import { ElMessage } from 'element-plus';
  // ElMessage.success('已成功退出登录');
};
</script>

<style scoped>
.teacher-dashboard-layout {
  min-height: 100vh;
  background-color: var(--el-bg-color-page); /* Use Element Plus page background variable */
}

.sidebar {
  background-color: #343a40; /* Keep dark background */
  box-shadow: 2px 0 5px rgba(0,0,0,0.1);
  /* el-aside handles width */
}

.sidebar-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between; /* Push user info to bottom */
}

.sidebar-title {
  color: var(--el-color-primary); /* Use Element Plus primary color */
  margin: 0;
  padding: 20px;
  text-align: center;
  font-size: 1.4em;
  font-weight: 600;
}

/* Remove default right border from vertical menu */
.el-menu-vertical-teacher {
  border-right: none;
  flex-grow: 1; /* Allow menu to fill space */
  overflow-y: auto; /* Scroll if menu items exceed height */
}

/* Customize active menu item background */
.el-menu-item.is-active {
  background-color: var(--el-color-primary-light-8) !important; /* Example active background */
  /* active-text-color handles text color */
}

/* Customize menu item hover background */
.el-menu-item:hover {
  background-color: #495057 !important; /* Darker hover background */
}

/* Icon styling */
.el-menu-item .el-icon {
  margin-right: 8px;
  vertical-align: middle;
}

.user-info {
  padding: 20px;
  text-align: center;
  border-top: 1px solid #495057; /* Separator line */
}

.user-info p {
  margin-bottom: 15px;
  font-size: 0.9em;
  color: #adb5bd; /* Lighter text color */
}

.logout-button {
  width: 100%;
  /* el-button styles are applied */
}

.main-content {
  padding: 20px; /* Adjust padding as needed */
  /* el-main handles background and basic layout */
}

/* Optional: Router View Transition */
.fade-transform-leave-active,
.fade-transform-enter-active {
  transition: all 0.3s ease;
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
