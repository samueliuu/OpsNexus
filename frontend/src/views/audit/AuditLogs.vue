<template>
  <div>
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0">操作审计日志</h3>
        <div>
          <el-button @click="exportLogs">导出</el-button>
        </div>
      </div>
      <div style="margin-bottom:12px;display:flex;gap:10px;flex-wrap:wrap">
        <el-input v-model="filterUsername" placeholder="用户名" clearable style="width:150px" @clear="page = 1; loadData()" @keyup.enter="page = 1; loadData()" />
        <el-select v-model="filterAction" placeholder="操作" clearable style="width:120px" @change="page = 1; loadData()">
          <el-option label="创建" value="create" /><el-option label="更新" value="update" /><el-option label="删除" value="delete" /><el-option label="读取" value="read" />
        </el-select>
        <el-select v-model="filterResource" placeholder="资源类型" clearable style="width:130px" @change="page = 1; loadData()">
          <el-option label="用户" value="user" /><el-option label="服务器" value="server" /><el-option label="告警规则" value="alert_rule" /><el-option label="数据中心" value="data_center" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态" clearable style="width:100px" @change="page = 1; loadData()">
          <el-option label="成功" value="success" /><el-option label="失败" value="failure" />
        </el-select>
        <el-button type="primary" @click="page = 1; loadData()">查询</el-button>
      </div>
      <el-table :data="tableData" stripe v-loading="loading" max-height="600">
        <el-table-column prop="username" label="用户" width="100" />
        <el-table-column prop="action" label="操作" width="80" />
        <el-table-column prop="resource_type" label="资源类型" width="110" />
        <el-table-column prop="resource_name" label="资源名称" min-width="140" />
        <el-table-column prop="ip_address" label="IP" width="130" />
        <el-table-column label="状态" width="70">
          <template #default="{ row }"><el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">{{ row.status === 'success' ? '成功' : '失败' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total, sizes, prev, pager, next" :page-sizes="[20, 50, 100]" @change="loadData" style="margin-top:16px;justify-content:flex-end" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { auditApi } from '@/api/outband-audit'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const loading = ref(false)
const tableData = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterUsername = ref('')
const filterAction = ref('')
const filterResource = ref('')
const filterStatus = ref('')

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
  } catch { ElMessage.error('加载审计日志失败') } finally { loading.value = false }
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
  } catch { ElMessage.error('导出失败') }
}
</script>
