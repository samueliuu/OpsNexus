import api from './request'

export const knowledgeApi = {
  query: (data: {
    question: string
    brand?: string
    model?: string
    category?: string
    query_type?: string
    conversation_id?: string
    top_k?: number
  }) => api.post('/knowledge/query', data),

  getSelCodes: (params: {
    brand: string
    event_code?: string
    severity?: string
    skip?: number
    limit?: number
  }) => api.get('/knowledge/sel-codes', { params }),

  getFirmwareMatrix: (params: {
    brand: string
    model?: string
    component?: string
    skip?: number
    limit?: number
  }) => api.get('/knowledge/firmware-matrix', { params }),

  createConversation: (data: { title: string }) =>
    api.post('/knowledge/conversations', data),

  listConversations: (params?: object) =>
    api.get('/knowledge/conversations', { params }),

  getConversation: (id: string) =>
    api.get(`/knowledge/conversations/${id}`),

  updateConversation: (id: string, data: { title: string }) =>
    api.patch(`/knowledge/conversations/${id}`, data),

  deleteConversation: (id: string) =>
    api.delete(`/knowledge/conversations/${id}`),

  createFavorite: (data: {
    message_id?: string
    title: string
    content: string
    source_type?: string
    brand?: string
  }) => api.post('/knowledge/favorites', data),

  listFavorites: (params?: object) =>
    api.get('/knowledge/favorites', { params }),

  deleteFavorite: (id: string) =>
    api.delete(`/knowledge/favorites/${id}`),
}
