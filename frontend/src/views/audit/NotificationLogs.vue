<template>
  <div>
    <Card>
      <template #content>
        <h3 style="margin:0 0 16px">通知记录</h3>
        <div style="margin-bottom:12px;display:flex;gap:10px">
          <Select v-model="filterChannelType" :options="channelTypeOptions" optionLabel="label" optionValue="value" placeholder="渠道类型" showClear style="width:130px" @change="page = 1; loadData()" />
          <Select v-model="filterStatus" :options="statusFilterOptions" optionLabel="label" optionValue="value" placeholder="状态" showClear style="width:110px" @change="page = 1; loadData()" />
          <Button :disabled="!selectedRows.length" @click="retrySelected">重试选中</Button>
        </div>
        <DataTable :value="tableData" striped :loading="loading" v-model:selection="selectedRows" dataKey="id">
          <Column selectionMode="multiple" style="width:50px" />
          <Column field="channel_type" header="渠道" style="width:90px" />
          <Column field="recipient" header="收件人" style="min-width:160px" />
          <Column field="subject" header="主题" style="min-width:140px" />
          <Column header="状态" style="width:80px">
            <template #body="{ data }"><Tag :severity="statusSeverity(data.status)" style="font-size:12px">{{ statusLabel(data.status) }}</Tag></template>
          </Column>
          <Column field="retry_count" header="重试" style="width:60px" />
          <Column header="发送时间" style="width:170px">
            <template #body="{ data }">{{ data.sent_at ? formatTime(data.sent_at) : '-' }}</template>
          </Column>
        </DataTable>
        <Paginator :rows="pageSize" :totalRecords="total" :first="(page - 1) * pageSize" @page="onPage" style="margin-top:16px" />
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { auditApi } from '@/api/outband-audit'
import { useToast } from 'primevue/usetoast'
import dayjs from 'dayjs'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Select from 'primevue/select'
import Paginator from 'primevue/paginator'

const toast = useToast()

const loading = ref(false)
const tableData = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterChannelType = ref<string | null>(null)
const filterStatus = ref<string | null>(null)
const selectedRows = ref<any[]>([])

const channelTypeOptions = [
  { label: '邮件', value: 'email' },
  { label: 'Webhook', value: 'webhook' },
  { label: '钉钉', value: 'dingtalk' },
  { label: '企业微信', value: 'wecom' },
  { label: '飞书', value: 'lark' },
]

const statusFilterOptions = [
  { label: '已发送', value: 'sent' },
  { label: '失败', value: 'failed' },
  { label: '重试中', value: 'retrying' },
  { label: '待发送', value: 'pending' },
]

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const params: any = { skip: (page.value - 1) * pageSize.value, limit: pageSize.value }
    if (filterChannelType.value) params.channel_type = filterChannelType.value
    if (filterStatus.value) params.status = filterStatus.value
    const { data } = await auditApi.notifications.list(params)
    tableData.value = data.items || []
    total.value = data.total || 0
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '加载失败', life: 3000 }) } finally { loading.value = false }
}

function onPage(event: any) {
  page.value = Math.floor(event.first / event.rows) + 1
  pageSize.value = event.rows
  loadData()
}

function statusSeverity(s: string) {
  const map: Record<string, string> = { sent: 'success', failed: 'danger', retrying: 'warning', pending: 'secondary' }
  return map[s] || 'secondary'
}

function statusLabel(s: string) {
  const map: Record<string, string> = { sent: '已发送', failed: '失败', retrying: '重试中', pending: '待发送' }
  return map[s] || s
}

function formatTime(t?: string) { return t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-' }

async function retrySelected() {
  const ids = selectedRows.value.map((r: any) => r.id)
  if (!ids.length) return
  try { await auditApi.notifications.retry(ids); toast.add({ severity: 'success', summary: '成功', detail: '重试已提交', life: 3000 }); loadData() } catch { toast.add({ severity: 'error', summary: '错误', detail: '重试失败', life: 3000 }) }
}
</script>
