<template>
  <div>
    <el-card shadow="never">
      <h3 style="margin:0 0 16px">通知记录</h3>
      <div style="margin-bottom:12px;display:flex;gap:10px">
        <el-select v-model="filterChannelType" placeholder="渠道类型" clearable style="width:130px" @change="page = 1; loadData()">
          <el-option label="邮件" value="email" /><el-option label="Webhook" value="webhook" /><el-option label="钉钉" value="dingtalk" /><el-option label="企业微信" value="wecom" /><el-option label="飞书" value="lark" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态" clearable style="width:110px" @change="page = 1; loadData()">
          <el-option label="已发送" value="sent" /><el-option label="失败" value="failed" /><el-option label="重试中" value="retrying" /><el-option label="待发送" value="pending" />
        </el-select>
        <el-button type="primary" @click="retrySelected" :disabled="!selectedIds.length">重试选中</el-button>
      </div>
      <el-table :data="tableData" stripe v-loading="loading" @selection-change="(rows: any[]) => selectedIds = rows.map((r: any) => r.id)">
        <el-table-column type="selection" width="50" :selectable="(row: any) => row.status === 'failed'" />
        <el-table-column prop="channel_type" label="渠道" width="90" />
        <el-table-column prop="recipient" label="收件人" min-width="160" />
        <el-table-column prop="subject" label="主题" min-width="140" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }"><el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="retry_count" label="重试" width="60" />
        <el-table-column label="发送时间" width="170">
          <template #default="{ row }">{{ row.sent_at ? formatTime(row.sent_at) : '-' }}</template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" layout="total, prev, pager, next" @change="loadData" style="margin-top:16px;justify-content:flex-end" />
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
const filterChannelType = ref('')
const filterStatus = ref('')
const selectedIds = ref<string[]>([])

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const params: any = { skip: (page.value - 1) * pageSize.value, limit: pageSize.value }
    if (filterChannelType.value) params.channel_type = filterChannelType.value
    if (filterStatus.value) params.status = filterStatus.value
    const { data } = await auditApi.notifications.list(params)
    tableData.value = data.items || []
    total.value = data.total || 0
  } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

function statusType(s: string) { return { sent: 'success', failed: 'danger', retrying: 'warning', pending: 'info' }[s] || 'info' }
function statusLabel(s: string) { return { sent: '已发送', failed: '失败', retrying: '重试中', pending: '待发送' }[s] || s }
function formatTime(t?: string) { return t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-' }

async function retrySelected() {
  try { await auditApi.notifications.retry(selectedIds.value); ElMessage.success('重试已提交'); loadData() } catch { ElMessage.error('重试失败') }
}
</script>
