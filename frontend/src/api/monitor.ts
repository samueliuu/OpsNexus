import api from './request'

export const monitorApi = {
  dashboard: () => api.get('/monitor/dashboard'),
  metricDefinitions: {
    list: (params?: object) => api.get('/monitor/definitions', { params }),
    get: (id: string) => api.get(`/monitor/definitions/${id}`),
    create: (data: object) => api.post('/monitor/definitions', data),
    update: (id: string, data: object) => api.put(`/monitor/definitions/${id}`, data),
    delete: (id: string) => api.delete(`/monitor/definitions/${id}`),
  },
  metricData: {
    write: (data: object) => api.post('/monitor/data', data),
    writeBatch: (data: object) => api.post('/monitor/data/batch', data),
    query: (data: object) => api.post('/monitor/data/query', data),
    latest: (metricName: string, serverId: string) =>
      api.get(`/monitor/data/latest/${metricName}/${serverId}`),
    cleanup: (retentionDays: number) =>
      api.delete('/monitor/data/cleanup', { params: { retention_days: retentionDays } }),
  },
  collect: (data?: object) => api.post('/monitor/collect', data || {}),
  evaluate: () => api.post('/monitor/evaluate'),
  alertRules: {
    list: (params?: object) => api.get('/monitor/rules', { params }),
    get: (id: string) => api.get(`/monitor/rules/${id}`),
    create: (data: object) => api.post('/monitor/rules', data),
    update: (id: string, data: object) => api.put(`/monitor/rules/${id}`, data),
    delete: (id: string) => api.delete(`/monitor/rules/${id}`),
  },
  alertEvents: {
    list: (params?: object) => api.get('/monitor/events', { params }),
    get: (id: string) => api.get(`/monitor/events/${id}`),
    acknowledge: (eventIds: string[]) =>
      api.post('/monitor/events/acknowledge', { event_ids: eventIds }),
    suppress: (eventIds: string[], reason?: string) =>
      api.post('/monitor/events/suppress', { event_ids: eventIds, reason }),
    stats: () => api.get('/monitor/events/stats'),
  },
}
