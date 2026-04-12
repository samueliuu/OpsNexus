<template>
  <div>
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6" v-for="stat in stats" :key="stat.label">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </el-card>
      </el-col>
    </el-row>
    <el-card shadow="hover">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>服务器监控</span>
          <el-button type="primary" size="small" @click="triggerCollect" :loading="collecting">手动采集</el-button>
        </div>
      </template>
      <el-table :data="summaries" stripe v-loading="loading" max-height="600">
        <el-table-column prop="server_name" label="服务器" min-width="120" />
        <el-table-column label="健康" width="80">
          <template #default="{ row }"><el-tag :type="healthType(row.health_status)" size="small">{{ healthLabel(row.health_status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="CPU温度" width="100">
          <template #default="{ row }">{{ row.cpu_temperature != null ? row.cpu_temperature.toFixed(1) + '°C' : '-' }}</template>
        </el-table-column>
        <el-table-column label="CPU使用率" width="140">
          <template #default="{ row }"><el-progress v-if="row.cpu_usage != null" :percentage="Math.round(row.cpu_usage)" :stroke-width="14" :color="usageColor(row.cpu_usage)" /><span v-else>-</span></template>
        </el-table-column>
        <el-table-column label="内存使用率" width="140">
          <template #default="{ row }"><el-progress v-if="row.memory_usage != null" :percentage="Math.round(row.memory_usage)" :stroke-width="14" :color="usageColor(row.memory_usage)" /><span v-else>-</span></template>
        </el-table-column>
        <el-table-column label="功耗" width="100">
          <template #default="{ row }">{{ row.power_consumption != null ? Math.round(row.power_consumption) + 'W' : '-' }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { monitorApi } from '@/api/monitor'
import { ElMessage } from 'element-plus'

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
  } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

async function triggerCollect() {
  collecting.value = true
  try {
    const { data } = await monitorApi.collect()
    ElMessage.success(`采集完成: ${data.collected_servers}台成功, ${data.failed_servers}台失败`)
    loadData()
  } catch { ElMessage.error('手动采集失败') } finally { collecting.value = false }
}

function healthType(s: string) { return { healthy: 'success', alerting: 'danger', offline: 'info', unknown: 'warning' }[s] || 'info' }
function healthLabel(s: string) { return { healthy: '健康', alerting: '告警', offline: '离线', unknown: '未知' }[s] || s }
function usageColor(v: number) { return v >= 90 ? '#f56c6c' : v >= 70 ? '#e6a23c' : '#67c23a' }
</script>

<style scoped>
.stat-row { margin-bottom: 20px; }
.stat-card { text-align: center; padding: 10px 0; }
.stat-value { font-size: 28px; font-weight: 700; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
</style>
