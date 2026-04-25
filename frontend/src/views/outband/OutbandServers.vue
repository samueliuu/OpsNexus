<template>
  <div>
    <Card>
      <template #content>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h3 style="margin:0">服务器带外管理</h3>
          <Button @click="testDialogVisible = true">测试连接</Button>
        </div>
        <DataTable :value="tableData" striped :loading="loading">
          <Column field="name" header="服务器" style="min-width:120px" />
          <Column field="brand" header="品牌" style="width:80px" />
          <Column header="BMC IP" style="width:140px">
            <template #body="{ data }">{{ data.bmc_info?.bmc_ip || '-' }}</template>
          </Column>
          <Column header="BMC状态" style="width:90px">
            <template #body="{ data }"><Tag :severity="data.bmc_info?.bmc_status === 'online' ? 'success' : data.bmc_info?.bmc_status === 'error' ? 'danger' : 'secondary'" style="font-size:12px">{{ data.bmc_info?.bmc_status || '未知' }}</Tag></template>
          </Column>
          <Column header="操作" style="width:320px">
            <template #body="{ data }">
              <div style="display:flex;gap:4px">
                <Button link size="small" @click="loadPower(data)" :disabled="!data.bmc_ip">电源</Button>
                <Button link size="small" severity="success" @click="loadSensors(data)" :disabled="!data.bmc_ip">传感器</Button>
                <Button link size="small" severity="warning" @click="loadFirmware(data)" :disabled="!data.bmc_ip">固件</Button>
                <Button link size="small" severity="secondary" @click="openKvm(data)" :disabled="!data.bmc_ip">KVM</Button>
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>
    <Dialog v-model:visible="powerDialogVisible" header="电源控制" :style="{ width: '400px' }">
      <div v-if="currentPower" style="margin-bottom:16px">
        当前状态: <Tag :severity="currentPower.power_state === 'on' ? 'success' : 'danger'">{{ currentPower.power_state }}</Tag>
      </div>
      <div style="display:flex;gap:4px">
        <Button severity="success" @click="doPower('on')">开机</Button>
        <Button severity="danger" @click="doPower('graceful_off')">关机</Button>
        <Button severity="warning" @click="doPower('restart')">重启</Button>
        <Button @click="doPower('force_off')">强制关机</Button>
      </div>
    </Dialog>
    <Dialog v-model:visible="sensorDialogVisible" header="传感器数据" :style="{ width: '700px' }">
      <DataTable :value="sensorData" striped :scrollable="true" scrollHeight="400px">
        <Column field="name" header="名称" style="min-width:150px" />
        <Column header="读数" style="width:120px"><template #body="{ data }">{{ data.reading ?? '-' }} {{ data.unit }}</template></Column>
        <Column field="status" header="状态" style="width:80px" />
        <Column field="sensor_type" header="类型" style="width:100px" />
      </DataTable>
    </Dialog>
    <Dialog v-model:visible="firmwareDialogVisible" header="固件清单" :style="{ width: '600px' }">
      <DataTable :value="firmwareData" striped :scrollable="true" scrollHeight="400px">
        <Column field="component" header="组件" style="min-width:120px" />
        <Column field="current_version" header="当前版本" style="width:150px" />
        <Column field="available_version" header="可用版本" style="width:150px" />
        <Column field="update_status" header="状态" style="width:100px" />
      </DataTable>
    </Dialog>
    <Dialog v-model:visible="testDialogVisible" header="测试BMC连接" :style="{ width: '450px' }" :modal="true">
      <div class="field">
        <label>地址</label>
        <InputText v-model="testForm.host" style="width:100%" />
      </div>
      <div class="field">
        <label>用户名</label>
        <InputText v-model="testForm.username" style="width:100%" />
      </div>
      <div class="field">
        <label>密码</label>
        <InputText v-model="testForm.password" type="password" style="width:100%" />
      </div>
      <div v-if="testResult" style="margin-top:12px">
        <Message :severity="testResult.success ? 'success' : 'error'">{{ testResult.message }}</Message>
        <div v-if="testResult.success" style="margin-top:12px;display:grid;grid-template-columns:auto 1fr;gap:8px 16px;border:1px solid var(--p-surface-200);border-radius:6px;padding:12px">
          <span style="font-weight:500;color:var(--p-text-muted-color)">品牌</span><span>{{ testResult.detected_brand }}</span>
          <span style="font-weight:500;color:var(--p-text-muted-color)">型号</span><span>{{ testResult.model }}</span>
        </div>
      </div>
      <template #footer>
        <Button label="关闭" @click="testDialogVisible=false" />
        <Button label="测试" :loading="testLoading" @click="doTest" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { serverApi } from '@/api/asset'
import { outbandApi } from '@/api/outband-audit'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'

const toast = useToast()
const confirm = useConfirm()

const loading = ref(false)
const tableData = ref<any[]>([])
const currentServerId = ref('')
const currentPower = ref<any>(null)
const powerDialogVisible = ref(false)
const sensorDialogVisible = ref(false)
const sensorData = ref<any[]>([])
const testDialogVisible = ref(false)
const testLoading = ref(false)
const testResult = ref<any>(null)
const testForm = ref({ host: '', username: '', password: '' })
const firmwareDialogVisible = ref(false)
const firmwareData = ref<any[]>([])

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const { data } = await serverApi.list({ limit: 200 })
    tableData.value = data.items || []
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '加载失败', life: 3000 }) } finally { loading.value = false }
}

async function loadPower(row: any) {
  try {
    const { data } = await outbandApi.getPowerState(row.id)
    currentPower.value = data
    currentServerId.value = row.id
    powerDialogVisible.value = true
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 3000 }) }
}

async function doPower(action: string) {
  confirm.require({
    message: `确认执行${action}操作？`,
    header: '电源操作',
    icon: 'pi pi-exclamation-triangle',
    acceptProps: { severity: 'warning' },
    accept: async () => {
      try {
        await outbandApi.setPowerAction(currentServerId.value, action)
        toast.add({ severity: 'success', summary: '成功', detail: '操作已发送', life: 3000 })
        powerDialogVisible.value = false
      } catch { toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 3000 }) }
    },
  })
}

async function loadSensors(row: any) {
  try {
    const { data } = await outbandApi.getSensorData(row.id)
    sensorData.value = data.sensors || []
    sensorDialogVisible.value = true
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 3000 }) }
}

async function loadFirmware(row: any) {
  try {
    const { data } = await outbandApi.getFirmware(row.id)
    firmwareData.value = data.firmware || []
    firmwareDialogVisible.value = true
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 3000 }) }
}

async function openKvm(row: any) {
  try {
    const { data } = await outbandApi.startKvm(row.id)
    const expires = data.expires_at ? new Date(data.expires_at).toLocaleString() : '未知'
    toast.add({ severity: 'success', summary: '成功', detail: `KVM会话已创建，有效期至 ${expires}`, life: 3000 })
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 3000 }) }
}

async function doTest() {
  testLoading.value = true
  testResult.value = null
  try {
    const { data } = await outbandApi.testConnection(testForm.value)
    testResult.value = data
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '连接测试失败', life: 3000 }) } finally { testLoading.value = false }
}
</script>
