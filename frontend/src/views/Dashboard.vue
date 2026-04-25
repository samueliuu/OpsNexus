<template>
  <div class="dashboard">
    <div class="stat-grid">
      <Card v-for="stat in stats" :key="stat.label">
        <template #content>
          <div class="stat-content">
            <div>
              <div class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
            <div class="stat-icon" :style="{ background: stat.bg }">
              <i :class="stat.icon" :style="{ color: stat.color }"></i>
            </div>
          </div>
        </template>
      </Card>
    </div>
    <div class="content-grid-2">
      <Card>
        <template #title>服务器概览</template>
        <template #content>
          <DataTable :value="serverSummaries" stripedRows :loading="loading" :rows="10" tableStyle="min-width: 50rem">
            <Column field="server_name" header="服务器" style="min-width: 120px" />
            <Column header="健康状态" style="width: 100px">
              <template #body="{ data }">
                <Tag :value="healthLabel(data.health_status)" :severity="healthSeverity(data.health_status)" />
              </template>
            </Column>
            <Column header="CPU温度" style="width: 100px">
              <template #body="{ data }">
                <span v-if="data.cpu_temperature != null">{{ data.cpu_temperature.toFixed(1) }}°C</span>
                <span v-else class="text-muted">-</span>
              </template>
            </Column>
            <Column header="CPU使用率" style="width: 140px">
              <template #body="{ data }">
                <ProgressBar v-if="data.cpu_usage != null" :value="Math.round(data.cpu_usage)" :showValue="true" :style="{ height: '14px' }" />
                <span v-else class="text-muted">-</span>
              </template>
            </Column>
            <Column header="内存使用率" style="width: 140px">
              <template #body="{ data }">
                <ProgressBar v-if="data.memory_usage != null" :value="Math.round(data.memory_usage)" :showValue="true" :style="{ height: '14px' }" />
                <span v-else class="text-muted">-</span>
              </template>
            </Column>
            <Column header="功耗" style="width: 100px">
              <template #body="{ data }">
                <span v-if="data.power_consumption != null">{{ Math.round(data.power_consumption) }}W</span>
                <span v-else class="text-muted">-</span>
              </template>
            </Column>
          </DataTable>
        </template>
      </Card>
      <Card>
        <template #title>
          <div style="display:flex;justify-content:space-between;align-items:center;width:100%">
            <span>活跃告警</span>
            <Button label="查看全部" link @click="$router.push('/monitor/alert-events')" />
          </div>
        </template>
        <template #content>
          <div v-if="alertEvents.length === 0" class="empty-state">
            <i class="pi pi-check-circle" style="color: var(--success)"></i>
            <p>暂无活跃告警</p>
          </div>
          <div v-else class="alert-list">
            <div v-for="event in alertEvents" :key="event.id" class="alert-item" :class="`alert-${event.severity}`">
              <div class="alert-header">
                <Tag :value="event.severity" :severity="severitySeverity(event.severity)" />
                <span class="alert-server">{{ event.server_name || event.server_id }}</span>
              </div>
              <div class="alert-summary">{{ event.summary }}</div>
              <div class="alert-time">{{ formatTime(event.triggered_at) }}</div>
            </div>
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { monitorApi } from '@/api/monitor'
import { useToast } from 'primevue/usetoast'
import dayjs from 'dayjs'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import Button from 'primevue/button'

const toast = useToast()
const loading = ref(false)
const serverSummaries = ref<any[]>([])
const alertEvents = ref<any[]>([])

const stats = ref([
  { label: '服务器总数', value: 0, icon: 'pi pi-server', color: 'var(--brand-primary)', bg: 'rgba(37,99,235,0.08)' },
  { label: '在线服务器', value: 0, icon: 'pi pi-check-circle', color: 'var(--success)', bg: 'rgba(16,185,129,0.08)' },
  { label: '严重告警', value: 0, icon: 'pi pi-exclamation-triangle', color: 'var(--danger)', bg: 'rgba(239,68,68,0.08)' },
  { label: '警告告警', value: 0, icon: 'pi pi-exclamation-circle', color: 'var(--warning)', bg: 'rgba(245,158,11,0.08)' },
])

onMounted(async () => {
  loading.value = true
  try {
    const [dashboardRes, alertRes] = await Promise.all([
      monitorApi.dashboard(),
      monitorApi.alertEvents.list({ status: 'firing', limit: 10 }),
    ])
    const data = dashboardRes.data
    serverSummaries.value = data.server_summaries || []
    stats.value[0].value = data.total_servers ?? 0
    stats.value[1].value = data.online_servers ?? 0
    stats.value[2].value = data.critical_alerts ?? 0
    stats.value[3].value = data.warning_alerts ?? 0
    alertEvents.value = alertRes.data.items || []
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '加载仪表盘数据失败', life: 3000 })
  } finally {
    loading.value = false
  }
})

function healthSeverity(status: string) {
  const map: Record<string, string> = { healthy: 'success', alerting: 'danger', offline: 'secondary', unknown: 'warning' }
  return map[status] || 'secondary'
}
function healthLabel(status: string) {
  const map: Record<string, string> = { healthy: '健康', alerting: '告警', offline: '离线', unknown: '未知' }
  return map[status] || status
}
function severitySeverity(severity: string) {
  const map: Record<string, string> = { critical: 'danger', warning: 'warning', info: 'info' }
  return map[severity] || 'info'
}
function formatTime(t: string) { return t ? dayjs(t).format('MM-DD HH:mm') : '-' }
</script>

<style scoped>
.stat-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  line-height: 1.2;
}
.stat-label {
  font-size: 0.8125rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}
.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
}
.stat-icon i {
  font-size: 1.25rem;
}
.alert-list {
  max-height: 460px;
  overflow-y: auto;
}
</style>
