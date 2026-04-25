<template>
  <div class="knowledge-assistant">
    <div class="sidebar">
      <div class="sidebar-header">
        <Button label="新建对话" icon="pi pi-plus" @click="createNewConversation" style="width: 100%" size="small" />
      </div>
      <div class="conversation-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          :class="['conversation-item', { active: currentConversationId === conv.id }]"
          @click="selectConversation(conv)"
        >
          <div class="conv-title">{{ conv.title }}</div>
          <div class="conv-time">{{ formatTime(conv.updated_at) }}</div>
          <Button
            class="conv-delete"
            size="small"
            link
            @click.stop="deleteConversation(conv.id)"
          >
            <i class="pi pi-trash"></i>
          </Button>
        </div>
      </div>
    </div>
    <div class="chat-main">
      <div class="chat-area" ref="chatAreaRef">
        <div v-if="messages.length === 0" class="welcome-section">
          <h2>OpsNexus 运维知识助手</h2>
          <p>输入您的问题，获取服务器运维知识指导</p>
          <div class="quick-actions">
            <Button v-for="q in quickQuestions" :key="q" :label="q" rounded @click="askQuick(q)" />
          </div>
        </div>
        <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
          <div class="message-avatar">
            <i v-if="msg.role === 'user'" class="pi pi-user" style="font-size: 20px"></i>
            <i v-else class="pi pi-desktop" style="font-size: 20px"></i>
          </div>
          <div class="message-body">
            <div class="message-content" v-html="renderContent(msg.content)"></div>
            <div v-if="msg.sources && msg.sources.length" class="message-sources">
              <Accordion>
                <AccordionPanel value="0">
                  <AccordionHeader>参考来源</AccordionHeader>
                  <AccordionContent>
                    <div v-for="(s, i) in msg.sources" :key="i" class="source-item">
                      <span v-if="s.document_title" class="source-title">{{ s.document_title }}</span>
                      <span v-if="s.chunk_text" class="source-text">{{ s.chunk_text.slice(0, 200) }}...</span>
                    </div>
                  </AccordionContent>
                </AccordionPanel>
              </Accordion>
            </div>
            <div v-if="msg.role === 'assistant'" class="message-actions">
              <Button size="small" link @click="copyMessage(msg.content)"><i class="pi pi-copy"></i> 复制</Button>
              <Button size="small" link @click="favoriteMessage(msg)"><i class="pi pi-star"></i> 收藏</Button>
            </div>
          </div>
        </div>
        <div v-if="loading" class="message assistant">
          <div class="message-avatar"><i class="pi pi-desktop" style="font-size: 20px"></i></div>
          <div class="message-body"><div class="typing-indicator"><span></span><span></span><span></span></div></div>
        </div>
      </div>
      <div class="input-area">
        <div class="input-options">
          <Select v-model="queryBrand" :options="brandOptions" optionLabel="label" optionValue="value" placeholder="选择品牌" showClear style="width: 120px" size="small" />
          <Select v-model="queryType" :options="queryTypeOptions" optionLabel="label" optionValue="value" style="width: 120px" size="small" />
        </div>
        <div class="input-row">
          <InputText
            v-model="inputText"
            placeholder="输入您的运维问题..."
            @keyup.enter="handleSend"
            size="large"
            :disabled="loading"
            style="flex: 1"
          />
          <Button label="发送" :loading="loading" @click="handleSend" :disabled="!inputText.trim()" size="large" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import { knowledgeApi } from '@/api/knowledge'

const toast = useToast()
const chatAreaRef = ref()
const inputText = ref('')
const loading = ref(false)
const queryBrand = ref('')
const queryType = ref('semantic')
const messages = ref<Array<{ role: string; content: string; sources?: any[]; message_id?: string }>>([])
const conversations = ref<Array<{ id: string; title: string; updated_at: string }>>([])
const currentConversationId = ref<string | null>(null)

const brandOptions = [
  { label: 'Dell', value: 'Dell' },
  { label: 'HPE', value: 'HPE' },
  { label: 'Lenovo', value: 'Lenovo' },
  { label: 'Huawei', value: 'Huawei' },
  { label: 'Inspur', value: 'Inspur' },
  { label: 'H3C', value: 'H3C' },
  { label: 'Sugon', value: 'Sugon' },
  { label: 'xFusion', value: 'xFusion' },
]

const queryTypeOptions = [
  { label: 'AI问答', value: 'semantic' },
  { label: '结构化查询', value: 'structured' },
  { label: '混合查询', value: 'hybrid' },
]

const quickQuestions = [
  'Dell R750 CPU温度过高怎么处理？',
  'HPE iLO无法连接怎么排查？',
  '华为iBMC SEL日志如何查看？',
  '服务器固件升级前需要做什么准备？',
]

const formatTime = (t: string) => {
  const d = new Date(t)
  const now = new Date()
  if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatAreaRef.value) chatAreaRef.value.scrollTop = chatAreaRef.value.scrollHeight
}

const renderContent = (content: string) => {
  return content.replace(/\n/g, '<br>')
}

const loadConversations = async () => {
  try {
    const { data } = await knowledgeApi.listConversations({ limit: 50 })
    conversations.value = data.items || []
  } catch { /* ignore */ }
}

const selectConversation = async (conv: { id: string; title: string; updated_at: string }) => {
  currentConversationId.value = conv.id
  messages.value = []
  try {
    const { data } = await knowledgeApi.getConversation(conv.id)
    if (data.messages) {
      messages.value = data.messages.map((m: any) => ({
        role: m.role,
        content: m.content,
        sources: m.sources,
        message_id: m.id,
      }))
    }
  } catch { /* ignore */ }
  scrollToBottom()
}

const createNewConversation = async () => {
  try {
    const { data } = await knowledgeApi.createConversation({ title: '新对话' })
    currentConversationId.value = data.id
    messages.value = []
    await loadConversations()
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '创建对话失败', life: 3000 })
  }
}

const deleteConversation = async (id: string) => {
  try {
    await knowledgeApi.deleteConversation(id)
    if (currentConversationId.value === id) {
      currentConversationId.value = null
      messages.value = []
    }
    await loadConversations()
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '删除失败', life: 3000 })
  }
}

const handleSend = async () => {
  const question = inputText.value.trim()
  if (!question || loading.value) return

  if (!currentConversationId.value) {
    try {
      const { data } = await knowledgeApi.createConversation({ title: question.slice(0, 30) })
      currentConversationId.value = data.id
      await loadConversations()
    } catch { /* ignore */ }
  }

  messages.value.push({ role: 'user', content: question })
  inputText.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const { data } = await knowledgeApi.query({
      question,
      brand: queryBrand.value || undefined,
      query_type: queryType.value,
      conversation_id: currentConversationId.value || undefined,
      top_k: 5,
    })
    messages.value.push({
      role: 'assistant',
      content: data.answer || '未找到相关信息',
      sources: data.sources || [],
      message_id: data.message_id,
    })
  } catch {
    messages.value.push({ role: 'assistant', content: '查询失败，请稍后重试。' })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

const askQuick = (q: string) => {
  inputText.value = q
  handleSend()
}

const copyMessage = (content: string) => {
  navigator.clipboard.writeText(content)
  toast.add({ severity: 'success', summary: '成功', detail: '已复制', life: 3000 })
}

const favoriteMessage = async (msg: any) => {
  try {
    await knowledgeApi.createFavorite({
      message_id: msg.message_id,
      title: msg.content.slice(0, 50),
      content: msg.content,
      source_type: 'qa',
      brand: queryBrand.value || undefined,
    })
    toast.add({ severity: 'success', summary: '成功', detail: '已收藏', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '收藏失败', life: 3000 })
  }
}

onMounted(() => {
  loadConversations()
})
</script>

<style scoped>
.knowledge-assistant {
  display: flex;
  height: calc(100vh - 120px);
  background: var(--surface-ground);
  border-radius: 8px;
  overflow: hidden;
}
.sidebar {
  width: 240px;
  background: var(--surface-card);
  border-right: 1px solid var(--surface-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.sidebar-header {
  padding: 12px;
  border-bottom: 1px solid var(--surface-border);
}
.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.conversation-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  position: relative;
  transition: background 0.2s;
}
.conversation-item:hover {
  background: var(--surface-hover);
}
.conversation-item.active {
  background: color-mix(in srgb, var(--primary-color) 10%, transparent);
}
.conv-title {
  font-size: 13px;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 24px;
}
.conv-time {
  font-size: 11px;
  color: var(--text-color-secondary);
  margin-top: 4px;
}
.conv-delete {
  position: absolute;
  right: 4px;
  top: 8px;
  opacity: 0;
  transition: opacity 0.2s;
}
.conversation-item:hover .conv-delete {
  opacity: 1;
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chat-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.welcome-section {
  text-align: center;
  padding: 60px 20px;
}
.welcome-section h2 {
  font-size: 24px;
  color: var(--text-color);
  margin-bottom: 8px;
}
.welcome-section p {
  color: var(--text-color-secondary);
  margin-bottom: 24px;
}
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}
.message.user {
  flex-direction: row-reverse;
}
.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.message.user .message-avatar {
  background: var(--primary-color);
  color: var(--primary-contrast-color);
}
.message.assistant .message-avatar {
  background: #22c55e;
  color: #fff;
}
.message-body {
  max-width: 70%;
}
.message.user .message-body {
  text-align: right;
}
.message-content {
  background: var(--surface-card);
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  color: var(--text-color);
}
.message.user .message-content {
  background: var(--primary-color);
  color: var(--primary-contrast-color);
}
.message-sources {
  margin-top: 8px;
}
.source-item {
  padding: 4px 0;
  font-size: 12px;
  color: var(--text-color-secondary);
}
.source-title {
  font-weight: 500;
  margin-right: 8px;
}
.source-text {
  color: var(--text-color-secondary);
}
.message-actions {
  margin-top: 4px;
  display: flex;
  gap: 4px;
}
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 16px;
}
.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-color-secondary);
  animation: typing 1.4s infinite;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-8px); }
}
.input-area {
  padding: 16px 20px;
  background: var(--surface-card);
  border-top: 1px solid var(--surface-border);
}
.input-options {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.input-row {
  display: flex;
  gap: 8px;
}
</style>
