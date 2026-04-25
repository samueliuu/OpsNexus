<template>
  <div class="knowledge-history">
    <div class="history-layout">
      <div class="history-sidebar">
        <Card class="conv-list-card">
          <template #header>
            <div class="card-header">
              <span>对话历史</span>
              <Button label="新建对话" size="small" @click="showNewDialog = true" />
            </div>
          </template>
          <template #content>
            <div class="loading-container" style="position: relative; min-height: 100px;">
              <div v-if="loadingConvs" class="loading-overlay">
                <ProgressSpinner style="width: 32px; height: 32px" />
              </div>
              <div class="conv-list">
                <div
                  v-for="conv in conversations"
                  :key="conv.id"
                  class="conv-item"
                  :class="{ active: currentConv?.id === conv.id }"
                  @click="selectConv(conv)"
                >
                  <div class="conv-info">
                    <div v-if="editingConvId === conv.id" class="conv-edit" @click.stop>
                      <InputText
                        v-model="editingTitle"
                        size="small"
                        @keyup.enter="saveTitle(conv.id)"
                        @keyup.escape="cancelEdit"
                        @blur="saveTitle(conv.id)"
                        ref="editInputRef"
                        style="width: 100%"
                      />
                    </div>
                    <div v-else class="conv-title" @dblclick.stop="startEdit(conv)">
                      {{ conv.title }}
                    </div>
                    <div class="conv-time">{{ formatTime(conv.updated_at) }}</div>
                  </div>
                  <div class="conv-actions">
                    <Button size="small" link @click.stop="startEdit(conv)" title="编辑标题">
                      <i class="pi pi-pencil"></i>
                    </Button>
                    <Button size="small" link severity="danger" @click.stop="deleteConv(conv.id)" title="删除对话">
                      <i class="pi pi-trash"></i>
                    </Button>
                  </div>
                </div>
                <div v-if="!loadingConvs && !conversations.length" class="empty-state">
                  <i class="pi pi-inbox" style="font-size: 36px; color: var(--text-color-secondary)"></i>
                  <p>暂无对话记录</p>
                  <p class="empty-hint">点击上方"新建对话"开始提问</p>
                </div>
              </div>
            </div>
          </template>
        </Card>
      </div>
      <div class="history-main">
        <Card class="conv-detail-card">
          <template #header>
            <div class="card-header">
              <span>{{ currentConv ? currentConv.title : '对话详情' }}</span>
            </div>
          </template>
          <template #content>
            <div v-if="currentConv" class="messages-list">
              <div v-for="msg in currentConv.messages" :key="msg.id" :class="['msg-item', msg.role]">
                <div class="msg-avatar">
                  <Avatar v-if="msg.role === 'user'" size="large" class="avatar-user" label="我" />
                  <Avatar v-else size="large" class="avatar-assistant" label="AI" />
                </div>
                <div class="msg-body">
                  <div class="msg-role">{{ msg.role === 'user' ? '我' : '助手' }}</div>
                  <div class="msg-content">{{ msg.content }}</div>
                </div>
              </div>
              <div v-if="!currentConv.messages?.length" class="empty-state">
                <i class="pi pi-inbox" style="font-size: 36px; color: var(--text-color-secondary)"></i>
                <p>暂无消息</p>
                <p class="empty-hint">在此对话中发送问题开始交流</p>
              </div>
            </div>
            <div v-else class="empty-state">
              <i class="pi pi-inbox" style="font-size: 48px; color: var(--text-color-secondary)"></i>
              <p>请从左侧选择一个对话</p>
            </div>
          </template>
        </Card>
      </div>
    </div>
    <Dialog v-model:visible="showNewDialog" header="新建对话" :style="{ width: '400px' }">
      <InputText v-model="newTitle" placeholder="输入对话标题" maxlength="256" style="width: 100%" />
      <template #footer>
        <Button label="取消" severity="secondary" @click="showNewDialog = false" />
        <Button label="创建" @click="createConv" :disabled="!newTitle.trim()" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Avatar from 'primevue/avatar'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'
import { knowledgeApi } from '@/api/knowledge'

const toast = useToast()
const loadingConvs = ref(false)
const conversations = ref<any[]>([])
const currentConv = ref<any>(null)
const showNewDialog = ref(false)
const newTitle = ref('')

const editingConvId = ref<string | null>(null)
const editingTitle = ref('')
const editInputRef = ref<any>(null)

const formatTime = (t: string) => {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const loadConversations = async () => {
  loadingConvs.value = true
  try {
    const { data } = await knowledgeApi.listConversations({ limit: 50 })
    conversations.value = data.items || []
  } catch { /* ignore */ } finally {
    loadingConvs.value = false
  }
}

const selectConv = async (conv: any) => {
  try {
    const { data } = await knowledgeApi.getConversation(conv.id)
    currentConv.value = data
  } catch { /* ignore */ }
}

const createConv = async () => {
  if (!newTitle.value.trim()) return
  try {
    await knowledgeApi.createConversation({ title: newTitle.value })
    newTitle.value = ''
    showNewDialog.value = false
    toast.add({ severity: 'success', summary: '成功', detail: '创建成功', life: 3000 })
    loadConversations()
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '创建失败', life: 3000 })
  }
}

const startEdit = (conv: any) => {
  editingConvId.value = conv.id
  editingTitle.value = conv.title
  nextTick(() => {
    editInputRef.value?.[0]?.$el?.focus()
  })
}

const cancelEdit = () => {
  editingConvId.value = null
  editingTitle.value = ''
}

const saveTitle = async (convId: string) => {
  if (!editingTitle.value.trim() || editingConvId.value !== convId) {
    cancelEdit()
    return
  }
  const conv = conversations.value.find(c => c.id === convId)
  if (conv && conv.title === editingTitle.value.trim()) {
    cancelEdit()
    return
  }
  try {
    await knowledgeApi.updateConversation(convId, { title: editingTitle.value.trim() })
    if (currentConv.value?.id === convId) {
      currentConv.value.title = editingTitle.value.trim()
    }
    toast.add({ severity: 'success', summary: '成功', detail: '标题已更新', life: 3000 })
    loadConversations()
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '更新失败', life: 3000 })
  } finally {
    cancelEdit()
  }
}

const deleteConv = async (id: string) => {
  try {
    await knowledgeApi.deleteConversation(id)
    if (currentConv.value?.id === id) currentConv.value = null
    toast.add({ severity: 'success', summary: '成功', detail: '已删除', life: 3000 })
    loadConversations()
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '删除失败', life: 3000 })
  }
}

onMounted(loadConversations)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }

.history-layout {
  display: flex;
  gap: 16px;
}
.history-sidebar {
  width: 33.333%;
  flex-shrink: 0;
}
.history-main {
  flex: 1;
}

.conv-list-card { height: calc(100vh - 160px); }
.conv-list-card :deep(.p-card-content) { padding: 8px; overflow-y: auto; height: calc(100% - 56px); }

.conv-detail-card { height: calc(100vh - 160px); }
.conv-detail-card :deep(.p-card-content) { padding: 16px; overflow-y: auto; height: calc(100% - 56px); }

.conv-list { display: flex; flex-direction: column; }

.conv-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
  transition: background 0.2s;
}
.conv-item:hover { background: var(--surface-hover); }
.conv-item.active { background: color-mix(in srgb, var(--primary-color) 10%, transparent); }

.conv-info { flex: 1; min-width: 0; }
.conv-title {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}
.conv-time { font-size: 12px; color: var(--text-color-secondary); margin-top: 2px; }
.conv-edit { width: 100%; }
.conv-actions { display: flex; gap: 0; opacity: 0; transition: opacity 0.2s; flex-shrink: 0; }
.conv-item:hover .conv-actions { opacity: 1; }

.messages-list { display: flex; flex-direction: column; gap: 16px; }

.msg-item {
  display: flex;
  gap: 12px;
  max-width: 85%;
}
.msg-item.user {
  flex-direction: row-reverse;
  align-self: flex-end;
}
.msg-item.assistant {
  align-self: flex-start;
}

.msg-avatar { flex-shrink: 0; margin-top: 2px; }
.avatar-user { background: var(--primary-color); font-size: 13px; }
.avatar-assistant { background: #22c55e; font-size: 13px; }

.msg-body { display: flex; flex-direction: column; }
.msg-item.user .msg-body { align-items: flex-end; }
.msg-item.assistant .msg-body { align-items: flex-start; }

.msg-role {
  font-size: 12px;
  color: var(--text-color-secondary);
  margin-bottom: 4px;
}

.msg-content {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}
.msg-item.assistant .msg-content {
  background: var(--surface-hover);
  color: var(--text-color);
  border-top-left-radius: 4px;
}
.msg-item.user .msg-content {
  background: var(--primary-color);
  color: var(--primary-contrast-color);
  border-top-right-radius: 4px;
}

.empty-state {
  text-align: center;
  padding: 40px 0;
  color: var(--text-color-secondary);
}
.empty-state p {
  margin: 8px 0 0;
}
.empty-hint { color: var(--text-color-secondary); font-size: 13px; margin: 0; }

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.7);
  z-index: 1;
}
</style>
