import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/system'

function isTokenExpired(tokenStr: string): boolean {
  if (!tokenStr) return true
  try {
    const parts = tokenStr.split('.')
    if (parts.length !== 3) return true
    const payload = JSON.parse(atob(parts[1]))
    if (typeof payload.exp !== 'number') return true
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

function safeJsonParse(str: string | null): any {
  if (!str) return null
  try { return JSON.parse(str) } catch { return null }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')
  const user = ref<any>(safeJsonParse(localStorage.getItem('user')))

  const isLoggedIn = computed(() => !!token.value && !isTokenExpired(token.value))
  const username = computed(() => user.value?.username || '')
  const roles = computed(() => user.value?.roles?.map((r: any) => r.code) || [])
  const isSuperAdmin = computed(() => roles.value.includes('super_admin'))

  async function login(usernameVal: string, password: string) {
    const { data } = await authApi.login({ username: usernameVal, password })
    token.value = data.access_token
    refreshToken.value = data.refresh_token
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    user.value = data.user
    if (data.user) {
      localStorage.setItem('user', JSON.stringify(data.user))
    }
  }

  async function fetchUser() {
    try {
      const { data } = await authApi.me()
      user.value = data
      localStorage.setItem('user', JSON.stringify(data))
    } catch (error: any) {
      if (error.response?.status === 401 || error.response?.status === 403) {
        logout()
      }
    }
  }

  function logout() {
    token.value = ''
    refreshToken.value = ''
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    const currentPath = window.location.pathname + window.location.search
    const redirectParam = currentPath !== '/login' ? `?redirect=${encodeURIComponent(currentPath)}` : ''
    window.location.href = `/login${redirectParam}`
  }

  function updateTokens(newAccessToken: string, newRefreshToken?: string) {
    token.value = newAccessToken
    localStorage.setItem('access_token', newAccessToken)
    if (newRefreshToken) {
      refreshToken.value = newRefreshToken
      localStorage.setItem('refresh_token', newRefreshToken)
    }
  }

  function hasPermission(resource: string, action: string): boolean {
    if (isSuperAdmin.value) return true
    return user.value?.roles?.some((role: any) =>
      role.permissions?.some(
        (p: any) => p.resource === resource && p.action === action
      )
    ) || false
  }

  return {
    token, refreshToken, user, isLoggedIn, username, roles, isSuperAdmin,
    login, fetchUser, logout, updateTokens, hasPermission,
  }
})
