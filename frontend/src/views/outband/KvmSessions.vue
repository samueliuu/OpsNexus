<template>
  <div>
    <el-card shadow="never">
      <h3 style="margin:0 0 16px">KVM 会话</h3>
      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column prop="server_id" label="服务器ID" width="280" />
        <el-table-column prop="user_id" label="用户ID" width="280" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column label="开始时间" width="170"><template #default="{ row }">{{ formatTime(row.started_at) }}</template></el-table-column>
        <el-table-column label="过期时间" width="170"><template #default="{ row }">{{ formatTime(row.expires_at) }}</template></el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-popconfirm v-if="row.status === 'active'" title="确认终止?" @confirm="terminate(row.id)"><template #reference><el-button text type="danger" size="small">终止</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { outbandApi } from '@/api/outband-audit'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const loading = ref(false)
const tableData = ref<any[]>([])

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try { const { data } = await outbandApi.listKvmSessions({ limit: 100 }); tableData.value = data || [] } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

async function terminate(id: string) {
  try { await outbandApi.terminateKvm(id); ElMessage.success('已终止'); loadData() } catch { ElMessage.error('终止会话失败') }
}

function formatTime(t?: string) { return t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-' }
</script>
