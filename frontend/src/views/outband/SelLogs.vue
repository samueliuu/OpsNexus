<template>
  <div>
    <Card>
      <template #content>
        <h3 style="margin:0 0 16px">SEL 日志</h3>
        <div style="margin-bottom:12px;display:flex;gap:10px;align-items:center">
          <Select v-model="filterServer" :options="servers" optionLabel="name" optionValue="id" placeholder="服务器" showClear style="width:200px" @change="onFilterChange" />
          <Select v-model="filterSeverity" :options="severityOptions" optionLabel="label" optionValue="value" placeholder="级别" showClear style="width:120px" @change="onFilterChange" />
          <Button size="small" :disabled="!selectedIds.length" @click="acknowledgeSelected">确认选中</Button>
        </div>
        <DataTable :value="tableData" striped :loading="loading" v-model:selection="selectedRows" :rowSelectable="(data: any) => !data.is_acknowledged" dataKey="id">
          <Column selectionMode="multiple" style="width:50px" />
          <Column field="timestamp" header="时间" style="width:170px"><template #body="{ data }">{{ formatTime(data.timestamp) }}</template></Column>
          <Column field="severity" header="级别" style="width:90px"><template #body="{ data }"><Tag :severity="data.severity === 'Critical' ? 'danger' : data.severity === 'Warning' ? 'warning' : 'secondary'" style="font-size:12px">{{ data.severity }}</Tag></template></Column>
          <Column field="sensor_type" header="传感器类型" style="width:120px" />
          <Column field="sensor_name" header="传感器" style="width:120px" />
          <Column field="description" header="描述" style="min-width:200px" />
          <Column header="已确认" style="width:80px"><template #body="{ data }"><i v-if="data.is_acknowledged" class="pi pi-check-circle" style="color:#4caf50"></i><span v-else>-</span></template></Column>
        </DataTable>
        <Paginator :rows="pageSize" :totalRecords="total" :first="(page - 1) * pageSize" @page="onPage" style="margin-top:16px" />
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { serverApi } from '@/api/asset'
import { outbandApi } from '@/api/outband-audit'
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
const pageSize = ref(50)
const servers = ref<any[]>([])
const filterServer = ref<string | null>(null)
const filterSeverity = ref<string | null>(null)
const selectedRows = ref<any[]>([])
const selectedIds = ref<string[]>([])

const severityOptions = [
  { label: 'Critical', value: 'Critical' },
  { label: 'Warning', value: 'Warning' },
  { label: 'Info', value: 'OK' },
]

onMounted(async () => {
  try { const { data } = await serverApi.list({ limit: 200 }); servers.value = data.items || [] } catch { toast.add({ severity: 'error', summary: '错误', detail: '加载服务器列表失败', life: 3000 }) }
  loadData()
})

function onFilterChange() {
  page.value = 1
  loadData()
}

function onPage(event: any) {
  page.value = Math.floor(event.first / event.rows) + 1
  pageSize.value = event.rows
  loadData()
}

async function acknowledgeSelected() {
  const ids = selectedRows.value.map((r: any) => r.id)
  if (!ids.length) return
  try {
    const { data } = await outbandApi.acknowledgeSel(ids)
    toast.add({ severity: 'success', summary: '成功', detail: `已确认 ${data.acknowledged || 0} 条`, life: 3000 })
    selectedRows.value = []
    loadData()
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 3000 }) }
}

async function loadData() {
  loading.value = true
  try {
    const params: any = { skip: (page.value - 1) * pageSize.value, limit: pageSize.value }
    if (filterServer.value) params.server_id = filterServer.value
    if (filterSeverity.value) params.severity = filterSeverity.value
    const { data } = await outbandApi.getSelLogs(params)
    tableData.value = data.items || []
    total.value = data.total || 0
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '加载失败', life: 3000 }) } finally { loading.value = false }
}

function formatTime(t?: string) { return t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-' }
</script>
