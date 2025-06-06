import { createRouter, createWebHistory } from 'vue-router';
import LoginView from '../views/Login.vue';
import StudentView from '../views/StudentDashboard.vue';
import TeacherView from '../views/TeacherDashboard.vue'; // 现在是 TeacherDashboard.vue
import AdminView from '../views/AdminDashboard.vue'; // 现在是 AdminDashboard.vue

// 导入教师界面的子组件 (保持不变)
import TeacherTimetable from '../components/TeacherTimetable.vue';
import TeacherSchedulingRequest from '../components/TeacherSchedulingRequest.vue';

// 导入管理员界面的子组件 (新增)
import AdminTeacherTimetable from '../components/AdminTeacherTimetable.vue';
import AdminStudentTimetable from '../components/AdminStudentTimetable.vue';
import AdminManualScheduling from '../components/AdminManualScheduling.vue';
import AdminImportCoursePlan from '../components/AdminImportCoursePlan.vue';


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/login' // 默认重定向到登录页
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView
    },
    {
      path: '/student',
      name: 'student',
      component: StudentView,
      // meta: { requiresAuth: true, role: 'student' } // TODO: 添加路由守卫元信息
    },
    {
      path: '/teacher',
      name: 'teacher-dashboard',
      component: TeacherView,
      redirect: '/teacher/timetable', // 教师界面默认重定向到课表页面
      children: [
        {
          path: 'timetable',
          name: 'teacher-timetable',
          component: TeacherTimetable
        },
        {
          path: 'scheduling-request',
          name: 'teacher-scheduling-request',
          component: TeacherSchedulingRequest
        }
      ],
      // meta: { requiresAuth: true, role: 'teacher' } // TODO: 添加路由守卫元信息
    },

    {
      path: '/admin',
      name: 'admin-dashboard', // 将名称更改为更具体的 "admin-dashboard"
      component: AdminView, // AdminView 现在是 AdminDashboard.vue
      redirect: '/admin/import-course-plan', // 管理员界面默认重定向到导入课程计划
      children: [
        {
          path: 'import-course-plan',
          name: 'admin-import-course-plan',
          component: AdminImportCoursePlan
        },
        {
          path: 'teacher-timetable',
          name: 'admin-teacher-timetable',
          component: AdminTeacherTimetable
        },
        {
          path: 'student-timetable',
          name: 'admin-student-timetable',
          component: AdminStudentTimetable
        },
        {
          path: 'manual-scheduling',
          name: 'admin-manual-scheduling',
          component: AdminManualScheduling
        },
        // 还可以根据图片添加其他管理员功能，例如查看课表
        {
          path: 'view-schedules',
          name: 'admin-view-schedules',
          component: AdminTeacherTimetable // 暂时复用，或创建新组件
        }
        // TODO: 添加其他管理员子路由 (如 /admin/users, /admin/courses 等)
        // {
        //   path: 'users',
        //   name: 'admin-users',
        //   component: () => import('../components/AdminUsersView.vue'), // 可以按需加载
        // },
      ],
      // meta: { requiresAuth: true, role: 'admin' } // TODO: 添加路由守卫元信息
    },
    // TODO: 添加其他管理员子路由 (如 /admin/users, /admin/courses 等)
    // {
    //   path: '/admin/users',
    //   name: 'admin-users',
    //   component: () => import('../views/AdminUsersView.vue'), // 可以按需加载
    //   meta: { requiresAuth: true, role: 'admin' }
    // },
    // ...其他管理页面路由
  ]
});

// TODO: 实现路由守卫 (Navigation Guard)
/*
router.beforeEach((to, from, next) => {
  const requiresAuth = to.meta.requiresAuth;
  const userRole = localStorage.getItem('userRole'); // 从本地存储获取用户角色
  const isLoggedIn = localStorage.getItem('token') != null; // 检查是否有 token

  if (requiresAuth && !isLoggedIn) {
    // 需要认证但未登录，跳转到登录页
    next('/login');
  } else if (requiresAuth && isLoggedIn && to.meta.role && to.meta.role !== userRole) {
    // 需要认证，已登录，但角色不匹配，可以跳转到错误页或首页
    alert('您没有权限访问此页面！'); // 简单提示
    // next('/'); // 或者 next('/student') 根据实际需求
    if (userRole === 'admin') next('/admin');
    else if (userRole === 'teacher') next('/teacher');
    else if (userRole === 'student') next('/student');
    else next('/login'); // 未知角色或无角色，回到登录
  } else {
    // 其他情况正常放行
    next();
  }
});
*/

export default router;
