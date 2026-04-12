import axios, { type InternalAxiosRequestConfig, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retry?: boolean
  }
}

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

function onTokenRefreshed(token: string) {
  refreshSubscribers.forEach(cb => cb(token))
  refreshSubscribers = []
}

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken && !error.config._retry) {
        error.config._retry = true

        if (isRefreshing) {
          return new Promise((resolve) => {
            subscribeTokenRefresh((newToken: string) => {
              error.config.headers.Authorization = `Bearer ${newToken}`
              resolve(api(error.config))
            })
          })
        }

        isRefreshing = true
        try {
          const { data } = await axios.post('/api/v1/system/auth/refresh', {
            refresh_token: refreshToken,
          })
          const authStore = useAuthStore()
          authStore.updateTokens(data.access_token, data.refresh_token)
          onTokenRefreshed(data.access_token)
          error.config.headers.Authorization = `Bearer ${data.access_token}`
          return api(error.config)
        } catch {
          const authStore = useAuthStore()
          authStore.logout()
          return Promise.reject(new Error('Authentication failed'))
        } finally {
          isRefreshing = false
        }
      } else {
        const authStore = useAuthStore()
        authStore.logout()
        return Promise.reject(new Error('Authentication failed'))
      }
    } else if (error.response?.data?.error?.message) {
      ElMessage.error(error.response.data.error.message)
    } else if (error.response?.data?.detail) {
      ElMessage.error(error.response.data.detail)
    } else {
      ElMessage.error(error.message || '请求失败')
    }
    return Promise.reject(error)
  }
)

export default api
