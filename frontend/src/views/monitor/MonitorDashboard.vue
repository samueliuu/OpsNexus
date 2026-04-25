<template>
  <div>
    <div class="stat-grid">
      <Card v-for="stat in stats" :key="stat.label" class="stat-card">
        <template #content>
          <div class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </template>
      </Card>
    </div>
    <Card>
      <template #header>
        <div class="card-header">
          <span>服务器监控</span>
          <Button label="手动采集" size="small" :loading="collecting" @click="triggerCollect" />
        </div>
      </template>
      <template #content>
        <DataTable :value="summaries" stripedRows :loading="loading" scrollable scrollHeight="600px">
          <Column field="server_name" header="服务器" style="min-width:120px" />
          <Column header="健康" style="width:80px">
            <template #body="{ data }">
              <Tag :severity="healthSeverity(data.health_status)">{{ healthLabel(data.health_status) }}</Tag>
            </template>
          </Column>
          <Column header="CPU温度" style="width:100px">
            <template #body="{ data }">{{ data.cpu_temperature != null ? data.cpu_temperature.toFixed(1) + '°C' : '-' }}</template>
          </Column>
          <Column header="CPU使用率" style="width:140px">
            <template #body="{ data }">
              <ProgressBar v-if="data.cpu_usage != null" :value="Math.round(data.cpu_usage)" :style="{ height: '14px' }" :severity="usageSeverity(data.cpu_usage)" />
              <span v-else>-</span>
            </template>
          </Column>
          <Column header="内存使用率" style="width:140px">
            <template #body="{ data }">
              <ProgressBar v-if="data.memory_usage != null" :value="Math.round(data.memory_usage)" :style="{ height: '14px' }" :severity="usageSeverity(data.memory_usage)" />
              <span v-else>-</span>
            </template>
          </Column>
          <Column header="功耗" style="width:100px">
            <template #body="{ data }">{{ data.power_consumption != null ? Math.round(data.power_consumption) + 'W' : '-' }}</template>
          </Column>
        </DataTable>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import { useToast } from 'primevue/usetoast'
import { monitorApi } from '@/api/monitor'

const toast = useToast()
const loading = ref(false)
const collecting = ref(false)
const summaries = ref<any[]>([])
const stats = ref([
  { label: '服务器总数', value: 0, color: '#409eff' },
  { label: '在线', value: 0, color: '#67c23a' },
  { label: '告警中', value: 0, color: '#f56c6c' },
  { label: '严重告警', value: 0, color: '#e6a23c' },
])

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const { data } = await monitorApi.dashboard()
    summaries.value = data.server_summaries || []
    stats.value[0].value = data.total_servers ?? 0
    stats.value[1].value = data.online_servers ?? 0
    stats.value[2].value = data.alerting_servers ?? 0
    stats.value[3].value = data.critical_alerts ?? 0
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '加载失败', life: 3000 })
  } finally {
    loading.value = false
  }
}

async function triggerCollect() {
  collecting.value = true
  try {
    const { data } = await monitorApi.collect()
    toast.add({ severity: 'success', summary: '成功', detail: `采集完成: ${data.collected_servers}台成功, ${data.failed_servers}台失败`, life: 3000 })
    loadData()
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '手动采集失败', life: 3000 })
  } finally {
    collecting.value = false
  }
}

function healthSeverity(s: string) {
  return { healthy: 'success', alerting: 'danger', offline: 'secondary', unknown: 'warning' }[s] || 'secondary'
}

function healthLabel(s: string) {
  return { healthy: '健康', alerting: '告警', offline: '离线', unknown: '未知' }[s] || s
}

function usageSeverity(v: number) {
  return v >= 90 ? 'danger' : v >= 70 ? 'warning' : 'success'
}
</script>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}
.stat-card { text-align: center; }
.stat-card :deep(.p-card-content) { padding: 10px 0; }
.stat-value { font-size: 28px; font-weight: 700; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
}
</style>
