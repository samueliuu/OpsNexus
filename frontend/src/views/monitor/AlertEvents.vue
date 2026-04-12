<template>
  <div>
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0">告警事件</h3>
        <div>
          <el-select v-model="filterStatus" placeholder="状态" clearable style="width:120px;margin-right:10px" @change="page = 1; loadData()">
            <el-option label="触发中" value="firing" /><el-option label="已确认" value="acknowledged" /><el-option label="已解决" value="resolved" /><el-option label="已抑制" value="suppressed" />
          </el-select>
          <el-select v-model="filterSeverity" placeholder="级别" clearable style="width:120px;margin-right:10px" @change="page = 1; loadData()">
            <el-option label="严重" value="critical" /><el-option label="警告" value="warning" /><el-option label="信息" value="info" />
          </el-select>
          <el-button type="primary" size="small" @click="acknowledgeSelected" :disabled="!selectedIds.length">确认选中</el-button>
        </div>
      </div>
      <el-table :data="tableData" stripe v-loading="loading" @selection-change="(rows: any[]) => selectedIds = rows.map((r: any) => r.id)">
        <el-table-column type="selection" width="50" />
        <el-table-column label="级别" width="80">
          <template #default="{ row }"><el-tag :type="sevType(row.severity)" size="small">{{ row.severity }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="summary" label="摘要" min-width="200" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }"><el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="指标值" width="100">
          <template #default="{ row }">{{ row.metric_value != null ? Number(row.metric_value).toFixed(2) : '-' }}</template>
        </el-table-column>
        <el-table-column label="触发时间" width="160">
          <template #default="{ row }">{{ formatTime(row.triggered_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'firing'" text type="primary" size="small" @click="acknowledgeOne(row.id)">确认</el-button>
            <el-button v-if="row.status === 'firing' || row.status === 'acknowledged'" text type="warning" size="small" @click="suppressOne(row.id)">抑制</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total, sizes, prev, pager, next" :page-sizes="[20, 50, 100]" @change="loadData" style="margin-top:16px;justify-content:flex-end" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { monitorApi } from '@/api/monitor'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const loading = ref(false)
const tableData = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')
const filterSeverity = ref('')
const selectedIds = ref<string[]>([])

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
  } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

function sevType(s: string) { return { critical: 'danger', warning: 'warning', info: 'info' }[s] || 'info' }
function statusType(s: string) { return { firing: 'danger', acknowledged: 'warning', resolved: 'success', suppressed: 'info' }[s] || 'info' }
function statusLabel(s: string) { return { firing: '触发中', acknowledged: '已确认', resolved: '已解决', suppressed: '已抑制' }[s] || s }
function formatTime(t?: string) { return t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-' }

async function acknowledgeOne(id: string) {
  try { await monitorApi.alertEvents.acknowledge([id]); ElMessage.success('已确认'); loadData() } catch { ElMessage.error('确认失败') }
}

async function acknowledgeSelected() {
  try { await monitorApi.alertEvents.acknowledge(selectedIds.value); ElMessage.success(`已确认 ${selectedIds.value.length} 条`); loadData() } catch { ElMessage.error('确认失败') }
}

async function suppressOne(id: string) {
  try { await monitorApi.alertEvents.suppress([id]); ElMessage.success('已抑制'); loadData() } catch { ElMessage.error('抑制失败') }
}
</script>
