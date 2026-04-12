<template>
  <div>
    <el-card shadow="never">
      <h3 style="margin:0 0 16px">SEL 日志</h3>
      <div style="margin-bottom:12px">
        <el-select v-model="filterServer" placeholder="服务器" clearable style="width:200px;margin-right:10px" @change="onFilterChange">
          <el-option v-for="s in servers" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <el-select v-model="filterSeverity" placeholder="级别" clearable style="width:120px;margin-right:10px" @change="onFilterChange">
          <el-option label="Critical" value="Critical" /><el-option label="Warning" value="Warning" /><el-option label="Info" value="OK" />
        </el-select>
        <el-button type="primary" size="small" :disabled="!selectedIds.length" @click="acknowledgeSelected">确认选中</el-button>
      </div>
      <el-table :data="tableData" stripe v-loading="loading" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" :selectable="(row: any) => !row.is_acknowledged" />
        <el-table-column prop="timestamp" label="时间" width="170"><template #default="{ row }">{{ formatTime(row.timestamp) }}</template></el-table-column>
        <el-table-column prop="severity" label="级别" width="90"><template #default="{ row }"><el-tag :type="row.severity === 'Critical' ? 'danger' : row.severity === 'Warning' ? 'warning' : 'info'" size="small">{{ row.severity }}</el-tag></template></el-table-column>
        <el-table-column prop="sensor_type" label="传感器类型" width="120" />
        <el-table-column prop="sensor_name" label="传感器" width="120" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column label="已确认" width="80"><template #default="{ row }"><el-icon v-if="row.is_acknowledged" color="#67c23a"><CircleCheck /></el-icon><span v-else>-</span></template></el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total, prev, pager, next" @change="loadData" style="margin-top:16px;justify-content:flex-end" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { serverApi } from '@/api/asset'
import { outbandApi } from '@/api/outband-audit'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const loading = ref(false)
const tableData = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const servers = ref<any[]>([])
const filterServer = ref('')
const filterSeverity = ref('')
const selectedIds = ref<string[]>([])

onMounted(async () => {
  try { const { data } = await serverApi.list({ limit: 200 }); servers.value = data.items || [] } catch { ElMessage.error('加载服务器列表失败') }
  loadData()
})

function onFilterChange() {
  page.value = 1
  loadData()
}

function onSelectionChange(rows: any[]) {
  selectedIds.value = rows.map((r: any) => r.id)
}

async function acknowledgeSelected() {
  if (!selectedIds.value.length) return
  try {
    const { data } = await outbandApi.acknowledgeSel(selectedIds.value)
    ElMessage.success(`已确认 ${data.acknowledged || 0} 条`)
    selectedIds.value = []
    loadData()
  } catch { ElMessage.error('操作失败') }
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
  } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

function formatTime(t?: string) { return t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-' }
</script>
