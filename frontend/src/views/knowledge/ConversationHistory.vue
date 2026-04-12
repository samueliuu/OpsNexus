<template>
  <div class="knowledge-history">
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card class="conv-list-card">
          <template #header>
            <div class="card-header">
              <span>对话历史</span>
              <el-button type="primary" size="small" @click="showNewDialog = true">新建对话</el-button>
            </div>
          </template>
          <div v-loading="loadingConvs" class="conv-list">
            <div
              v-for="conv in conversations"
              :key="conv.id"
              class="conv-item"
              :class="{ active: currentConv?.id === conv.id }"
              @click="selectConv(conv)"
            >
              <div class="conv-info">
                <div v-if="editingConvId === conv.id" class="conv-edit" @click.stop>
                  <el-input
                    v-model="editingTitle"
                    size="small"
                    @keyup.enter="saveTitle(conv.id)"
                    @keyup.escape="cancelEdit"
                    @blur="saveTitle(conv.id)"
                    ref="editInputRef"
                  />
                </div>
                <div v-else class="conv-title" @dblclick.stop="startEdit(conv)">
                  {{ conv.title }}
                </div>
                <div class="conv-time">{{ formatTime(conv.updated_at) }}</div>
              </div>
              <div class="conv-actions">
                <el-button size="small" text @click.stop="startEdit(conv)" title="编辑标题">
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button size="small" text type="danger" @click.stop="deleteConv(conv.id)" title="删除对话">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
            <el-empty v-if="!loadingConvs && !conversations.length" description="暂无对话记录" :image-size="80">
              <template #description>
                <p class="empty-hint">点击上方"新建对话"开始提问</p>
              </template>
            </el-empty>
          </div>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card class="conv-detail-card">
          <template #header>
            <div class="card-header">
              <span>{{ currentConv ? currentConv.title : '对话详情' }}</span>
            </div>
          </template>
          <div v-if="currentConv" class="messages-list">
            <div v-for="msg in currentConv.messages" :key="msg.id" :class="['msg-item', msg.role]">
              <div class="msg-avatar">
                <el-avatar v-if="msg.role === 'user'" :size="32" class="avatar-user">我</el-avatar>
                <el-avatar v-else :size="32" class="avatar-assistant">AI</el-avatar>
              </div>
              <div class="msg-body">
                <div class="msg-role">{{ msg.role === 'user' ? '我' : '助手' }}</div>
                <div class="msg-content">{{ msg.content }}</div>
              </div>
            </div>
            <el-empty v-if="!currentConv.messages?.length" description="暂无消息" :image-size="80">
              <template #description>
                <p class="empty-hint">在此对话中发送问题开始交流</p>
              </template>
            </el-empty>
          </div>
          <el-empty v-else description="请从左侧选择一个对话" :image-size="120" />
        </el-card>
      </el-col>
    </el-row>
    <el-dialog v-model="showNewDialog" title="新建对话" width="400px">
      <el-input v-model="newTitle" placeholder="输入对话标题" maxlength="256" show-word-limit />
      <template #footer>
        <el-button @click="showNewDialog = false">取消</el-button>
        <el-button type="primary" @click="createConv" :disabled="!newTitle.trim()">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { knowledgeApi } from '@/api/knowledge'
import { ElMessage } from 'element-plus'
import { Delete, Edit } from '@element-plus/icons-vue'

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
  } catch {} finally {
    loadingConvs.value = false
  }
}

const selectConv = async (conv: any) => {
  try {
    const { data } = await knowledgeApi.getConversation(conv.id)
    currentConv.value = data
  } catch {}
}

const createConv = async () => {
  if (!newTitle.value.trim()) return
  try {
    await knowledgeApi.createConversation({ title: newTitle.value })
    newTitle.value = ''
    showNewDialog.value = false
    ElMessage.success('创建成功')
    loadConversations()
  } catch {
    ElMessage.error('创建失败')
  }
}

const startEdit = (conv: any) => {
  editingConvId.value = conv.id
  editingTitle.value = conv.title
  nextTick(() => {
    editInputRef.value?.[0]?.focus()
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
    ElMessage.success('标题已更新')
    loadConversations()
  } catch {
    ElMessage.error('更新失败')
  } finally {
    cancelEdit()
  }
}

const deleteConv = async (id: string) => {
  try {
    await knowledgeApi.deleteConversation(id)
    if (currentConv.value?.id === id) currentConv.value = null
    ElMessage.success('已删除')
    loadConversations()
  } catch {
    ElMessage.error('删除失败')
  }
}

onMounted(loadConversations)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }

.conv-list-card { height: calc(100vh - 160px); }
.conv-list-card :deep(.el-card__body) { padding: 8px; overflow-y: auto; height: calc(100% - 56px); }

.conv-detail-card { height: calc(100vh - 160px); }
.conv-detail-card :deep(.el-card__body) { padding: 16px; overflow-y: auto; height: calc(100% - 56px); }

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
.conv-item:hover { background: #f5f7fa; }
.conv-item.active { background: #ecf5ff; }

.conv-info { flex: 1; min-width: 0; }
.conv-title {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}
.conv-time { font-size: 12px; color: #909399; margin-top: 2px; }
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
.avatar-user { background: #409eff; font-size: 13px; }
.avatar-assistant { background: #67c23a; font-size: 13px; }

.msg-body { display: flex; flex-direction: column; }
.msg-item.user .msg-body { align-items: flex-end; }
.msg-item.assistant .msg-body { align-items: flex-start; }

.msg-role {
  font-size: 12px;
  color: #909399;
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
  background: #f4f4f5;
  color: #303133;
  border-top-left-radius: 4px;
}
.msg-item.user .msg-content {
  background: #409eff;
  color: #ffffff;
  border-top-right-radius: 4px;
}

.empty-hint { color: #909399; font-size: 13px; margin: 0; }
</style>
