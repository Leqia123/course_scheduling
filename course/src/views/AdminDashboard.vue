<template>
  <el-container class="admin-dashboard-layout">
    <el-aside width="220px" class="sidebar">
      <div class="sidebar-content">
        <h2 class="sidebar-title">管理员功能</h2>
        <el-menu
          :default-active="activeMenu"
          class="el-menu-vertical-admin"
          router
          background-color="#343a40"
          text-color="#ffffff"
          active-text-color="#ffd04b"
          :collapse="isCollapsed"
        >
          <!-- 动态生成菜单项，或者像现在这样硬编码 -->
          <el-menu-item index="/admin/import-course-plan">
             <el-icon><DocumentAdd /></el-icon>
            <span>课程计划</span>
          </el-menu-item>
          <el-menu-item index="/admin/teacher-timetable">
             <el-icon><User /></el-icon>
            <span>查询教员课表</span>
          </el-menu-item>
          <el-menu-item index="/admin/student-timetable">
             <el-icon><Reading /></el-icon>
            <span>查询学生课表</span>
          </el-menu-item>
          <el-menu-item index="/admin/manual-scheduling">
             <el-icon><EditPen /></el-icon>
            <span>手动调整课表</span>
          </el-menu-item>
          <!-- 如果有更多管理模块，在这里添加 el-menu-item -->
          <!-- 示例：
          <el-sub-menu index="/admin/management">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统管理</span>
            </template>
            <el-menu-item index="/admin/management/users">用户管理</el-menu-item>
            <el-menu-item index="/admin/management/roles">角色管理</el-menu-item>
          </el-sub-menu>
          -->
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
      <!-- 这里是右侧内容区域 -->
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
  ElContainer, ElAside, ElMain, ElMenu, ElMenuItem, ElSubMenu, ElButton, ElIcon
} from 'element-plus';
// 引入需要的图标 (确保已安装 @element-plus/icons-vue)
import {
  DocumentAdd, User, Reading, EditPen, Setting, // 根据实际菜单项调整
} from '@element-plus/icons-vue';

const router = useRouter();
const route = useRoute(); // 获取当前路由信息
const loggedInUsername = ref('');
const isCollapsed = ref(false); // 控制菜单是否折叠，如果需要的话

onMounted(() => {
  loggedInUsername.value = localStorage.getItem('username') || '管理员用户';
});

// 计算当前激活的菜单项，基于当前路由路径
const activeMenu = computed(() => {
  const { path } = route;
  return path;
});

const logout = () => {
  // 清除用户登录状态和用户名
  localStorage.removeItem('token');
  localStorage.removeItem('userRole');
  localStorage.removeItem('username');
  router.push('/login'); // 跳转回登录页面
  // 可以选择性地提示用户已退出
  // import { ElMessage } from 'element-plus';
  // ElMessage.success('已成功退出登录');
};
</script>

<style scoped>
.admin-dashboard-layout {
  min-height: 100vh;
  background-color: var(--el-bg-color-page); /* 使用 Element Plus 的页面背景色变量 */
}

.sidebar {
  background-color: #343a40; /* 保持深色背景 */
  transition: width 0.3s;
  box-shadow: 2px 0 5px rgba(0,0,0,0.1);
  /* 如果需要折叠功能，需要调整 */
}

.sidebar-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between; /* 使 User Info 固定在底部 */
}


.sidebar-title {
  color: var(--el-color-primary); /* 使用 Element Plus 主题色 */
  margin: 0;
  padding: 20px;
  text-align: center;
  font-size: 1.4em;
  font-weight: 600;
}

/* 覆盖 el-menu 的默认边框 */
.el-menu-vertical-admin {
  border-right: none;
  flex-grow: 1; /* 让菜单占据标题和用户信息之间的所有可用空间 */
  overflow-y: auto; /* 如果菜单项过多，允许滚动 */
}

/* 定制菜单项激活时的背景色 (Element Plus 默认使用 active-text-color) */
.el-menu-item.is-active {
  background-color: var(--el-color-primary-light-8) !important; /* 可以自定义激活背景色 */
  color: var(--el-color-primary) !important; /* 确保激活文字颜色也正确 */
}
/* 鼠标悬停在菜单项上时的样式 */
.el-menu-item:hover {
  background-color: #495057 !important; /* 自定义悬停背景色 */
}

/* 侧边栏图标样式 */
.el-menu-item .el-icon,
.el-sub-menu__title .el-icon {
  margin-right: 8px;
  vertical-align: middle;
}

.user-info {
  padding: 20px;
  text-align: center;
  border-top: 1px solid #495057; /* 分割线 */
}

.user-info p {
  margin-bottom: 15px;
  font-size: 0.9em;
  color: #adb5bd; /* 浅灰色文字 */
}

.logout-button {
  width: 100%;
  /* el-button 已经有默认样式，可以按需调整 */
}

.main-content {
  padding: 20px;
  /* background-color: #fff;  Element Plus 默认 main 背景 */
  /* box-shadow: 0 0 10px rgba(0,0,0,0.05); */ /* Element Plus 默认无阴影 */
  /* margin: 20px; */ /* 通常 el-main 不加 margin */
  /* border-radius: 8px; */ /* el-main 默认无圆角 */
}

/* Router View 过渡动画 (可选) */
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
