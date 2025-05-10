import { createRouter, createWebHistory } from 'vue-router';
import Login from './Login.vue';
import Group from './Group.vue';
import Chat from './Chat.vue';

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/groups',
    name: 'Group',
    component: Group,
    meta: { requiresAuth: true }
  },
  {
    path: '/chat/:groupId',
    name: 'Chat',
    component: Chat,
    props: true,
    meta: { requiresAuth: true }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// 导航守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token');
  
  if (to.meta.requiresAuth && !token) {
    // 如果需要登录但没有token，则重定向到登录页面
    next('/login');
  } else if (to.path === '/login' && token) {
    // 如果已登录又访问登录页，重定向到群组页面
    next('/groups');
  } else {
    next();
  }
});

export default router;