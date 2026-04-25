<template>
  <div>
    <Card>
      <template #content>
        <h3 style="margin:0 0 16px">KVM 会话</h3>
        <DataTable :value="tableData" striped :loading="loading">
          <Column field="server_id" header="服务器ID" style="width:280px" />
          <Column field="user_id" header="用户ID" style="width:280px" />
          <Column header="状态" style="width:90px">
            <template #body="{ data }"><Tag :severity="data.status === 'active' ? 'success' : 'secondary'" style="font-size:12px">{{ data.status }}</Tag></template>
          </Column>
          <Column header="开始时间" style="width:170px"><template #body="{ data }">{{ formatTime(data.started_at) }}</template></Column>
          <Column header="过期时间" style="width:170px"><template #body="{ data }">{{ formatTime(data.expires_at) }}</template></Column>
          <Column header="操作" style="width:100px">
            <template #body="{ data }">
              <Button v-if="data.status === 'active'" link severity="danger" size="small" @click="confirmTerminate(data.id)">终止</Button>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { outbandApi } from '@/api/outband-audit'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import dayjs from 'dayjs'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import ConfirmDialog from 'primevue/confirmdialog'

const toast = useToast()
const confirm = useConfirm()

const loading = ref(false)
const tableData = ref<any[]>([])

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try { const { data } = await outbandApi.listKvmSessions({ limit: 100 }); tableData.value = data || [] } catch { toast.add({ severity: 'error', summary: '错误', detail: '加载失败', life: 3000 }) } finally { loading.value = false }
}

function confirmTerminate(id: string) {
  confirm.require({
    message: '确认终止?',
    header: '终止会话',
    icon: 'pi pi-exclamation-triangle',
    acceptProps: { severity: 'danger' },
    accept: async () => {
      try { await outbandApi.terminateKvm(id); toast.add({ severity: 'success', summary: '成功', detail: '已终止', life: 3000 }); loadData() } catch { toast.add({ severity: 'error', summary: '错误', detail: '终止会话失败', life: 3000 }) }
    },
  })
}

function formatTime(t?: string) { return t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-' }
</script>
