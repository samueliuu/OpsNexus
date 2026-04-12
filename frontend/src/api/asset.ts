import api from './request'

export const dataCenterApi = {
  list: (params?: object) => api.get('/asset/datacenters', { params }),
  get: (id: string) => api.get(`/asset/datacenters/${id}`),
  create: (data: object) => api.post('/asset/datacenters', data),
  update: (id: string, data: object) => api.put(`/asset/datacenters/${id}`, data),
  delete: (id: string) => api.delete(`/asset/datacenters/${id}`),
}

export const rackApi = {
  list: (params?: object) => api.get('/asset/racks', { params }),
  get: (id: string) => api.get(`/asset/racks/${id}`),
  create: (data: object) => api.post('/asset/racks', data),
  update: (id: string, data: object) => api.put(`/asset/racks/${id}`, data),
  delete: (id: string) => api.delete(`/asset/racks/${id}`),
}

export const serverApi = {
  list: (params?: object) => api.get('/asset/servers', { params }),
  get: (id: string) => api.get(`/asset/servers/${id}`),
  create: (data: object) => api.post('/asset/servers', data),
  update: (id: string, data: object) => api.put(`/asset/servers/${id}`, data),
  delete: (id: string) => api.delete(`/asset/servers/${id}`),
  bulkCreate: (data: object) => api.post('/asset/servers/bulk', data),
  bulkUpdate: (data: object) => api.put('/asset/servers/bulk', data),
  bulkDelete: (data: object) => api.delete('/asset/servers/bulk', { data }),
}

export const bmcCredentialApi = {
  get: (serverId: string) => api.get(`/asset/servers/${serverId}/bmc-credential`),
  save: (serverId: string, data: object) => api.put(`/asset/servers/${serverId}/bmc-credential`, data),
  delete: (credentialId: string) => api.delete(`/asset/bmc-credentials/${credentialId}`),
}
