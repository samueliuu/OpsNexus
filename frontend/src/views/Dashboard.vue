<template>
  <div class="dashboard">
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6" v-for="stat in stats" :key="stat.label">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-info">
              <div class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
            <el-icon :size="40" :style="{ color: stat.color }"><component :is="stat.icon" /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header><span>服务器概览</span></template>
          <el-table :data="serverSummaries" stripe style="width: 100%" max-height="500" v-loading="loading">
            <el-table-column prop="server_name" label="服务器" min-width="120" />
            <el-table-column label="健康状态" width="100">
              <template #default="{ row }">
                <el-tag :type="healthTagType(row.health_status)" size="small">{{ healthLabel(row.health_status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="CPU温度" width="100">
              <template #default="{ row }">
                <span v-if="row.cpu_temperature != null">{{ row.cpu_temperature.toFixed(1) }}°C</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="CPU使用率" width="120">
              <template #default="{ row }">
                <el-progress v-if="row.cpu_usage != null" :percentage="Math.round(row.cpu_usage)" :stroke-width="14" :color="usageColor(row.cpu_usage)" />
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="内存使用率" width="120">
              <template #default="{ row }">
                <el-progress v-if="row.memory_usage != null" :percentage="Math.round(row.memory_usage)" :stroke-width="14" :color="usageColor(row.memory_usage)" />
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="功耗" width="100">
              <template #default="{ row }">
                <span v-if="row.power_consumption != null">{{ Math.round(row.power_consumption) }}W</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="alert-card">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>活跃告警</span>
              <el-button text type="primary" @click="$router.push('/monitor/alert-events')">查看全部</el-button>
            </div>
          </template>
          <div v-if="alertEvents.length === 0" class="empty-alert">
            <el-icon :size="48" color="#67c23a"><CircleCheck /></el-icon>
            <p>暂无活跃告警</p>
          </div>
          <div v-else class="alert-list">
            <div v-for="event in alertEvents" :key="event.id" class="alert-item" :class="`alert-${event.severity}`">
              <div class="alert-header">
                <el-tag :type="severityTagType(event.severity)" size="small">{{ event.severity }}</el-tag>
                <span class="alert-server">{{ event.server_name || event.server_id }}</span>
              </div>
              <div class="alert-summary">{{ event.summary }}</div>
              <div class="alert-time">{{ formatTime(event.triggered_at) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { monitorApi } from '@/api/monitor'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const loading = ref(false)
const serverSummaries = ref<any[]>([])
const alertEvents = ref<any[]>([])

const stats = ref([
  { label: '服务器总数', value: 0, icon: 'Monitor', color: '#409eff' },
  { label: '在线服务器', value: 0, icon: 'CircleCheck', color: '#67c23a' },
  { label: '严重告警', value: 0, icon: 'WarningFilled', color: '#f56c6c' },
  { label: '警告告警', value: 0, icon: 'Warning', color: '#e6a23c' },
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
  } catch { ElMessage.error('加载仪表盘数据失败') } finally {
    loading.value = false
  }
})

function healthTagType(status: string) {
  const map: Record<string, string> = { healthy: 'success', alerting: 'danger', offline: 'info', unknown: 'warning' }
  return map[status] || 'info'
}
function healthLabel(status: string) {
  const map: Record<string, string> = { healthy: '健康', alerting: '告警', offline: '离线', unknown: '未知' }
  return map[status] || status
}
function usageColor(val: number) {
  if (val >= 90) return '#f56c6c'
  if (val >= 70) return '#e6a23c'
  return '#67c23a'
}
function severityTagType(severity: string) {
  const map: Record<string, string> = { critical: 'danger', warning: 'warning', info: 'info' }
  return map[severity] || 'info'
}
function formatTime(t: string) { return t ? dayjs(t).format('MM-DD HH:mm') : '-' }
</script>

<style scoped>
.stat-row { margin-bottom: 20px; }
.stat-card { cursor: default; }
.stat-content { display: flex; justify-content: space-between; align-items: center; }
.stat-value { font-size: 32px; font-weight: 700; }
.stat-label { font-size: 14px; color: #909399; margin-top: 4px; }
.text-muted { color: #c0c4cc; }
.alert-card { height: 100%; }
.empty-alert { text-align: center; padding: 40px 0; color: #909399; }
.alert-list { max-height: 460px; overflow-y: auto; }
.alert-item { padding: 12px; border-radius: 6px; margin-bottom: 8px; border-left: 3px solid; }
.alert-critical { border-color: #f56c6c; background: #fef0f0; }
.alert-warning { border-color: #e6a23c; background: #fdf6ec; }
.alert-info { border-color: #909399; background: #f4f4f5; }
.alert-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.alert-server { font-weight: 600; font-size: 13px; }
.alert-summary { font-size: 13px; color: #606266; margin-bottom: 4px; }
.alert-time { font-size: 12px; color: #909399; }
</style>
