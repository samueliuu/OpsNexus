<template>
  <div>
    <Card>
      <template #content>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h3 style="margin:0">告警事件</h3>
          <div style="display:flex;align-items:center;gap:10px">
            <Select v-model="filterStatus" :options="statusFilterOptions" optionLabel="label" optionValue="value" placeholder="状态" showClear style="width:120px" @change="onFilterChange" />
            <Select v-model="filterSeverity" :options="severityFilterOptions" optionLabel="label" optionValue="value" placeholder="级别" showClear style="width:120px" @change="onFilterChange" />
            <Button label="确认选中" size="small" @click="acknowledgeSelected" :disabled="!selectedIds.length" />
          </div>
        </div>
        <DataTable v-model:selection="selectedRows" :value="tableData" stripedRows :loading="loading">
          <Column selectionMode="multiple" style="width:50px" />
          <Column header="级别" style="width:80px">
            <template #body="{ data }">
              <Tag :severity="sevSeverity(data.severity)">{{ data.severity }}</Tag>
            </template>
          </Column>
          <Column field="summary" header="摘要" style="min-width:200px" />
          <Column header="状态" style="width:90px">
            <template #body="{ data }">
              <Tag :severity="statusSeverity(data.status)">{{ statusLabel(data.status) }}</Tag>
            </template>
          </Column>
          <Column header="指标值" style="width:100px">
            <template #body="{ data }">{{ data.metric_value != null ? Number(data.metric_value).toFixed(2) : '-' }}</template>
          </Column>
          <Column header="触发时间" style="width:160px">
            <template #body="{ data }">{{ formatTime(data.triggered_at) }}</template>
          </Column>
          <Column header="操作" style="width:120px" frozen alignFrozen="right">
            <template #body="{ data }">
              <Button v-if="data.status === 'firing'" label="确认" link size="small" @click="acknowledgeOne(data.id)" />
              <Button v-if="data.status === 'firing' || data.status === 'acknowledged'" label="抑制" link severity="warning" size="small" @click="suppressOne(data.id)" />
            </template>
          </Column>
        </DataTable>
        <Paginator :rows="pageSize" :totalRecords="total" :first="(page - 1) * pageSize" @page="onPage" :rowsPerPageOptions="[20, 50, 100]" template="RowsPerPageDropdown CurrentPageReport PrevPageLink PageLinks NextPageLink" currentPageReportTemplate="共 {totalRecords} 条" style="margin-top:16px" />
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import Paginator from 'primevue/paginator'
import { useToast } from 'primevue/usetoast'
import { monitorApi } from '@/api/monitor'
import dayjs from 'dayjs'

const toast = useToast()
const loading = ref(false)
const tableData = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')
const filterSeverity = ref('')
const selectedRows = ref<any[]>([])
const selectedIds = computed(() => selectedRows.value.map(r => r.id))

const statusFilterOptions = [
  { label: '触发中', value: 'firing' },
  { label: '已确认', value: 'acknowledged' },
  { label: '已解决', value: 'resolved' },
  { label: '已抑制', value: 'suppressed' },
]
const severityFilterOptions = [
  { label: '严重', value: 'critical' },
  { label: '警告', value: 'warning' },
  { label: '信息', value: 'info' },
]

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const params: any = { skip: (page.value - 1) * pageSize.value, limit: pageSize.value }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterSeverity.value) params.severity = filterSeverity.value
    const { data } = await monitorApi.alertEvents.list(params)
    tableData.value = data.items || []
    total.value = data.total || 0
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '加载失败', life: 3000 })
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  page.value = 1
  loadData()
}

function onPage(event: any) {
  page.value = event.page + 1
  pageSize.value = event.rows
  loadData()
}

function sevSeverity(s: string) {
  return { critical: 'danger', warning: 'warning', info: 'secondary' }[s] || 'secondary'
}

function statusSeverity(s: string) {
  return { firing: 'danger', acknowledged: 'warning', resolved: 'success', suppressed: 'secondary' }[s] || 'secondary'
}

function statusLabel(s: string) {
  return { firing: '触发中', acknowledged: '已确认', resolved: '已解决', suppressed: '已抑制' }[s] || s
}

function formatTime(t?: string) {
  return t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-'
}

async function acknowledgeOne(id: string) {
  try {
    await monitorApi.alertEvents.acknowledge([id])
    toast.add({ severity: 'success', summary: '成功', detail: '已确认', life: 3000 })
    loadData()
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '确认失败', life: 3000 })
  }
}

async function acknowledgeSelected() {
  try {
    await monitorApi.alertEvents.acknowledge(selectedIds.value)
    toast.add({ severity: 'success', summary: '成功', detail: `已确认 ${selectedIds.value.length} 条`, life: 3000 })
    loadData()
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '确认失败', life: 3000 })
  }
}

async function suppressOne(id: string) {
  try {
    await monitorApi.alertEvents.suppress([id])
    toast.add({ severity: 'success', summary: '成功', detail: '已抑制', life: 3000 })
    loadData()
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '抑制失败', life: 3000 })
  }
}
</script>
