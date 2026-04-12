<template>
  <div>
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0">服务器带外管理</h3>
        <el-button type="primary" @click="testDialogVisible = true">测试连接</el-button>
      </div>
      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column prop="name" label="服务器" min-width="120" />
        <el-table-column prop="brand" label="品牌" width="80" />
        <el-table-column label="BMC IP" width="140">
          <template #default="{ row }">{{ row.bmc_info?.bmc_ip || '-' }}</template>
        </el-table-column>
        <el-table-column label="BMC状态" width="90">
          <template #default="{ row }"><el-tag :type="row.bmc_info?.bmc_status === 'online' ? 'success' : row.bmc_info?.bmc_status === 'error' ? 'danger' : 'info'" size="small">{{ row.bmc_info?.bmc_status || '未知' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="loadPower(row)" :disabled="!row.bmc_ip">电源</el-button>
            <el-button text type="success" size="small" @click="loadSensors(row)" :disabled="!row.bmc_ip">传感器</el-button>
            <el-button text type="warning" size="small" @click="loadFirmware(row)" :disabled="!row.bmc_ip">固件</el-button>
            <el-button text type="info" size="small" @click="openKvm(row)" :disabled="!row.bmc_ip">KVM</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="powerDialogVisible" title="电源控制" width="400px">
      <div v-if="currentPower" style="margin-bottom:16px">
        当前状态: <el-tag :type="currentPower.power_state === 'on' ? 'success' : 'danger'">{{ currentPower.power_state }}</el-tag>
      </div>
      <el-button-group>
        <el-button type="success" @click="doPower('on')">开机</el-button>
        <el-button type="danger" @click="doPower('graceful_off')">关机</el-button>
        <el-button type="warning" @click="doPower('restart')">重启</el-button>
        <el-button @click="doPower('force_off')">强制关机</el-button>
      </el-button-group>
    </el-dialog>
    <el-dialog v-model="sensorDialogVisible" title="传感器数据" width="700px">
      <el-table :data="sensorData" stripe max-height="400">
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column label="读数" width="120"><template #default="{ row }">{{ row.reading ?? '-' }} {{ row.unit }}</template></el-table-column>
        <el-table-column prop="status" label="状态" width="80" />
        <el-table-column prop="sensor_type" label="类型" width="100" />
      </el-table>
    </el-dialog>
    <el-dialog v-model="firmwareDialogVisible" title="固件清单" width="600px">
      <el-table :data="firmwareData" stripe max-height="400">
        <el-table-column prop="component" label="组件" min-width="120" />
        <el-table-column prop="current_version" label="当前版本" width="150" />
        <el-table-column prop="available_version" label="可用版本" width="150" />
        <el-table-column prop="update_status" label="状态" width="100" />
      </el-table>
    </el-dialog>
    <el-dialog v-model="testDialogVisible" title="测试BMC连接" width="450px" destroy-on-close>
      <el-form :model="testForm" label-width="80px">
        <el-form-item label="地址"><el-input v-model="testForm.host" /></el-form-item>
        <el-form-item label="用户名"><el-input v-model="testForm.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="testForm.password" type="password" show-password /></el-form-item>
      </el-form>
      <div v-if="testResult" style="margin-top:12px">
        <el-alert :type="testResult.success ? 'success' : 'error'" :title="testResult.message" show-icon :closable="false" />
        <el-descriptions v-if="testResult.success" :column="1" border style="margin-top:12px" size="small">
          <el-descriptions-item label="品牌">{{ testResult.detected_brand }}</el-descriptions-item>
          <el-descriptions-item label="型号">{{ testResult.model }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer><el-button @click="testDialogVisible=false">关闭</el-button><el-button type="primary" :loading="testLoading" @click="doTest">测试</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { serverApi } from '@/api/asset'
import { outbandApi } from '@/api/outband-audit'
import { ElMessage, ElMessageBox } from 'element-plus'

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
  } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

async function loadPower(row: any) {
  try {
    const { data } = await outbandApi.getPowerState(row.id)
    currentPower.value = data
    currentServerId.value = row.id
    powerDialogVisible.value = true
  } catch { ElMessage.error('操作失败') }
}

async function doPower(action: string) {
  try {
    await ElMessageBox.confirm(`确认执行${action}操作？`, '电源操作', { type: 'warning' })
    await outbandApi.setPowerAction(currentServerId.value, action)
    ElMessage.success('操作已发送')
    powerDialogVisible.value = false
  } catch { ElMessage.error('操作失败') }
}

async function loadSensors(row: any) {
  try {
    const { data } = await outbandApi.getSensorData(row.id)
    sensorData.value = data.sensors || []
    sensorDialogVisible.value = true
  } catch { ElMessage.error('操作失败') }
}

async function loadFirmware(row: any) {
  try {
    const { data } = await outbandApi.getFirmware(row.id)
    firmwareData.value = data.firmware || []
    firmwareDialogVisible.value = true
  } catch { ElMessage.error('操作失败') }
}

async function openKvm(row: any) {
  try {
    const { data } = await outbandApi.startKvm(row.id)
    const expires = data.expires_at ? new Date(data.expires_at).toLocaleString() : '未知'
    ElMessage.success(`KVM会话已创建，有效期至 ${expires}`)
  } catch { ElMessage.error('操作失败') }
}

async function doTest() {
  testLoading.value = true
  testResult.value = null
  try {
    const { data } = await outbandApi.testConnection(testForm.value)
    testResult.value = data
  } catch { ElMessage.error('连接测试失败') } finally { testLoading.value = false }
}
</script>
