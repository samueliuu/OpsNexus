import api from './request'

export const outbandApi = {
  testConnection: (data: object) => api.post('/outband/test-connection', data),
  getSystemInfo: (serverId: string) => api.get(`/outband/servers/${serverId}/system-info`),
  getPowerState: (serverId: string) => api.get(`/outband/servers/${serverId}/power`),
  setPowerAction: (serverId: string, action: string) =>
    api.post(`/outband/servers/${serverId}/power`, { action }),
  bulkPowerAction: (serverIds: string[], action: string) =>
    api.post('/outband/servers/bulk-power', { server_ids: serverIds, action }),
  getSensorData: (serverId: string) => api.get(`/outband/servers/${serverId}/sensors`),
  getSelLogs: (params?: object) => api.get('/outband/sel-logs', { params }),
  acknowledgeSel: (entryIds: string[]) =>
    api.post('/outband/sel-logs/acknowledge', { entry_ids: entryIds }),
  getFirmware: (serverId: string) => api.get(`/outband/servers/${serverId}/firmware`),
  getHardware: (serverId: string) => api.get(`/outband/servers/${serverId}/hardware`),
  startKvm: (serverId: string, durationMinutes = 60) =>
    api.post(`/outband/servers/${serverId}/kvm`, { duration_minutes: durationMinutes }),
  terminateKvm: (sessionId: string) => api.delete(`/outband/kvm/${sessionId}`),
  listKvmSessions: (params?: object) => api.get('/outband/kvm-sessions', { params }),
}

export const auditApi = {
  logs: {
    list: (params?: object) => api.get('/audit/logs', { params }),
    get: (id: string) => api.get(`/audit/logs/${id}`),
    stats: (params?: object) => api.get('/audit/logs/stats', { params }),
    export: (params?: object) =>
      api.get('/audit/logs/export', { params, responseType: 'blob' }),
    cleanup: (retentionDays: number) =>
      api.delete('/audit/logs/cleanup', { params: { retention_days: retentionDays } }),
  },
  notifications: {
    send: (data: object) => api.post('/audit/notifications/send', data),
    list: (params?: object) => api.get('/audit/notifications', { params }),
    get: (id: string) => api.get(`/audit/notifications/${id}`),
    retry: (logIds: string[]) =>
      api.post('/audit/notifications/retry', { log_ids: logIds }),
    stats: () => api.get('/audit/notifications/stats'),
  },
}
