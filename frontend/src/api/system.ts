import api from './request'

export const authApi = {
  login: (data: { username: string; password: string }) =>
    api.post('/system/auth/login', data),
  register: (data: {
    username: string
    email: string
    password: string
    full_name?: string
    phone?: string
    user_type: string
    company?: string
    title?: string
  }) => api.post('/system/auth/register', data),
  refresh: (refresh_token: string) =>
    api.post('/system/auth/refresh', { refresh_token }),
  me: () => api.get('/system/auth/me'),
  changePassword: (userId: string, data: { old_password: string; new_password: string }) =>
    api.put(`/system/users/${userId}/password`, data),
  getWsTicket: () => api.post('/system/auth/ws-ticket'),
}

export const userApi = {
  list: (params?: object) => api.get('/system/users', { params }),
  get: (id: string) => api.get(`/system/users/${id}`),
  create: (data: object) => api.post('/system/users', data),
  update: (id: string, data: object) => api.put(`/system/users/${id}`, data),
  delete: (id: string) => api.delete(`/system/users/${id}`),
}

export const roleApi = {
  list: (params?: object) => api.get('/system/roles', { params }),
  get: (id: string) => api.get(`/system/roles/${id}`),
  create: (data: object) => api.post('/system/roles', data),
  update: (id: string, data: object) => api.put(`/system/roles/${id}`, data),
  delete: (id: string) => api.delete(`/system/roles/${id}`),
}

export const permissionApi = {
  list: () => api.get('/system/permissions'),
}

export const configApi = {
  list: (params?: object) => api.get('/system/configs', { params }),
  get: (id: string) => api.get(`/system/configs/${id}`),
  create: (data: object) => api.post('/system/configs', data),
  update: (id: string, data: object) => api.put(`/system/configs/${id}`, data),
  delete: (id: string) => api.delete(`/system/configs/${id}`),
}

export const channelApi = {
  list: (params?: object) => api.get('/system/notification-channels', { params }),
  get: (id: string) => api.get(`/system/notification-channels/${id}`),
  create: (data: object) => api.post('/system/notification-channels', data),
  update: (id: string, data: object) => api.put(`/system/notification-channels/${id}`, data),
  delete: (id: string) => api.delete(`/system/notification-channels/${id}`),
}
