import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/Register.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      children: [
        {
          path: '',
          redirect: '/knowledge/assistant',
        },
        {
          path: 'knowledge/assistant',
          name: 'KnowledgeAssistant',
          component: () => import('@/views/knowledge/KnowledgeAssistant.vue'),
        },
        {
          path: 'knowledge/sel-codes',
          name: 'SELQuery',
          component: () => import('@/views/knowledge/SELQuery.vue'),
        },
        {
          path: 'knowledge/firmware-matrix',
          name: 'FirmwareMatrix',
          component: () => import('@/views/knowledge/FirmwareMatrix.vue'),
        },
        {
          path: 'knowledge/conversations',
          name: 'ConversationHistory',
          component: () => import('@/views/knowledge/ConversationHistory.vue'),
        },
        {
          path: 'knowledge/favorites',
          name: 'KnowledgeFavorites',
          component: () => import('@/views/knowledge/Favorites.vue'),
        },
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/Dashboard.vue'),
        },
        {
          path: 'asset/data-centers',
          name: 'DataCenters',
          component: () => import('@/views/asset/DataCenters.vue'),
        },
        {
          path: 'asset/racks',
          name: 'Racks',
          component: () => import('@/views/asset/Racks.vue'),
        },
        {
          path: 'asset/servers',
          name: 'Servers',
          component: () => import('@/views/asset/Servers.vue'),
        },
        {
          path: 'asset/servers/:id',
          name: 'ServerDetail',
          component: () => import('@/views/asset/ServerDetail.vue'),
        },
        {
          path: 'monitor/dashboard',
          name: 'MonitorDashboard',
          component: () => import('@/views/monitor/MonitorDashboard.vue'),
        },
        {
          path: 'monitor/alert-rules',
          name: 'AlertRules',
          component: () => import('@/views/monitor/AlertRules.vue'),
        },
        {
          path: 'monitor/alert-events',
          name: 'AlertEvents',
          component: () => import('@/views/monitor/AlertEvents.vue'),
        },
        {
          path: 'outband/servers',
          name: 'OutbandServers',
          component: () => import('@/views/outband/OutbandServers.vue'),
        },
        {
          path: 'outband/sel-logs',
          name: 'SelLogs',
          component: () => import('@/views/outband/SelLogs.vue'),
        },
        {
          path: 'outband/kvm',
          name: 'KvmSessions',
          component: () => import('@/views/outband/KvmSessions.vue'),
        },
        {
          path: 'audit/logs',
          name: 'AuditLogs',
          component: () => import('@/views/audit/AuditLogs.vue'),
        },
        {
          path: 'audit/notifications',
          name: 'NotificationLogs',
          component: () => import('@/views/audit/NotificationLogs.vue'),
        },
        {
          path: 'system/users',
          name: 'Users',
          component: () => import('@/views/system/Users.vue'),
        },
        {
          path: 'system/roles',
          name: 'Roles',
          component: () => import('@/views/system/Roles.vue'),
        },
        {
          path: 'system/configs',
          name: 'Configs',
          component: () => import('@/views/system/Configs.vue'),
        },
        {
          path: 'system/channels',
          name: 'Channels',
          component: () => import('@/views/system/Channels.vue'),
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/NotFound.vue'),
      meta: { public: true },
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  if (to.meta.public) {
    if (to.path === '/login' && authStore.isLoggedIn) {
      next({ path: '/knowledge/assistant' })
      return
    }
    next()
    return
  }
  if (authStore.isLoggedIn) {
    if (!authStore.user) {
      try { await authStore.fetchUser() } catch {}
    }
    next()
  } else {
    next({ path: '/login', query: { redirect: to.fullPath } })
  }
})

export default router
