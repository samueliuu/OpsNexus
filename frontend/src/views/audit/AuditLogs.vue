<template>
  <div>
    <Card>
      <template #content>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h3 style="margin:0">操作审计日志</h3>
          <div>
            <Button @click="exportLogs">导出</Button>
          </div>
        </div>
        <div style="margin-bottom:12px;display:flex;gap:10px;flex-wrap:wrap">
          <InputText v-model="filterUsername" placeholder="用户名" @keyup.enter="page = 1; loadData()" style="width:150px" />
          <Select v-model="filterAction" :options="actionOptions" optionLabel="label" optionValue="value" placeholder="操作" showClear style="width:120px" @change="page = 1; loadData()" />
          <Select v-model="filterResource" :options="resourceOptions" optionLabel="label" optionValue="value" placeholder="资源类型" showClear style="width:130px" @change="page = 1; loadData()" />
          <Select v-model="filterStatus" :options="statusOptions" optionLabel="label" optionValue="value" placeholder="状态" showClear style="width:100px" @change="page = 1; loadData()" />
          <Button @click="page = 1; loadData()">查询</Button>
        </div>
        <DataTable :value="tableData" striped :loading="loading" :scrollable="true" scrollHeight="600px">
          <Column field="username" header="用户" style="width:100px" />
          <Column field="action" header="操作" style="width:80px" />
          <Column field="resource_type" header="资源类型" style="width:110px" />
          <Column field="resource_name" header="资源名称" style="min-width:140px" />
          <Column field="ip_address" header="IP" style="width:130px" />
          <Column header="状态" style="width:70px">
            <template #body="{ data }"><Tag :severity="data.status === 'success' ? 'success' : 'danger'" style="font-size:12px">{{ data.status === 'success' ? '成功' : '失败' }}</Tag></template>
          </Column>
          <Column header="时间" style="width:170px">
            <template #body="{ data }">{{ formatTime(data.created_at) }}</template>
          </Column>
        </DataTable>
        <Paginator :rows="pageSize" :totalRecords="total" :first="(page - 1) * pageSize" :rowsPerPageOptions="[20, 50, 100]" @page="onPage" style="margin-top:16px" />
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
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Paginator from 'primevue/paginator'

const toast = useToast()

const loading = ref(false)
const tableData = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterUsername = ref('')
const filterAction = ref<string | null>(null)
const filterResource = ref<string | null>(null)
const filterStatus = ref<string | null>(null)

const actionOptions = [
  { label: '创建', value: 'create' },
  { label: '更新', value: 'update' },
  { label: '删除', value: 'delete' },
  { label: '读取', value: 'read' },
]

const resourceOptions = [
  { label: '用户', value: 'user' },
  { label: '服务器', value: 'server' },
  { label: '告警规则', value: 'alert_rule' },
  { label: '数据中心', value: 'data_center' },
]

const statusOptions = [
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failure' },
]

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const params: any = { skip: (page.value - 1) * pageSize.value, limit: pageSize.value }
    if (filterUsername.value) params.username = filterUsername.value
    if (filterAction.value) params.action = filterAction.value
    if (filterResource.value) params.resource_type = filterResource.value
    if (filterStatus.value) params.status = filterStatus.value
    const { data } = await auditApi.logs.list(params)
    tableData.value = data.items || []
    total.value = data.total || 0
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '加载审计日志失败', life: 3000 }) } finally { loading.value = false }
}

function onPage(event: any) {
  page.value = Math.floor(event.first / event.rows) + 1
  pageSize.value = event.rows
  loadData()
}

function formatTime(t?: string) { return t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-' }

async function exportLogs() {
  try {
    const params: any = { format: 'csv' }
    if (filterUsername.value) params.username = filterUsername.value
    if (filterAction.value) params.action = filterAction.value
    if (filterResource.value) params.resource_type = filterResource.value
    if (filterStatus.value) params.status = filterStatus.value
    const { data } = await auditApi.logs.export(params)
    const url = URL.createObjectURL(new Blob([data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `audit_logs_${dayjs().format('YYYYMMDD_HHmmss')}.csv`
    link.click()
    URL.revokeObjectURL(url)
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '导出失败', life: 3000 }) }
}
</script>
