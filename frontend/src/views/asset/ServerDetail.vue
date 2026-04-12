<template>
  <div>
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0">服务器详情</h3>
        <el-button @click="$router.back()">返回</el-button>
      </div>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="基本信息" name="info">
          <el-descriptions :column="3" border v-loading="loading">
            <el-descriptions-item label="名称">{{ server.name }}</el-descriptions-item>
            <el-descriptions-item label="主机名">{{ server.hostname }}</el-descriptions-item>
            <el-descriptions-item label="品牌">{{ server.brand }}</el-descriptions-item>
            <el-descriptions-item label="型号">{{ server.model }}</el-descriptions-item>
            <el-descriptions-item label="序列号">{{ server.serial_number }}</el-descriptions-item>
            <el-descriptions-item label="状态"><el-tag :type="server.status === 'active' ? 'success' : 'info'" size="small">{{ server.status }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="BMC IP">{{ server.bmc_info?.bmc_ip || '-' }}</el-descriptions-item>
            <el-descriptions-item label="BMC状态"><el-tag :type="server.bmc_info?.bmc_status === 'online' ? 'success' : 'danger'" size="small">{{ server.bmc_info?.bmc_status || '-' }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="CPU">{{ server.hardware_info?.cpu_model || '-' }} × {{ server.hardware_info?.cpu_count ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="内存">{{ server.hardware_info?.memory_gb ?? '-' }} GB</el-descriptions-item>
            <el-descriptions-item label="操作系统">{{ server.software_info?.os_name || '-' }} {{ server.software_info?.os_version || '' }}</el-descriptions-item>
            <el-descriptions-item label="部门">{{ server.department }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
        <el-tab-pane label="带外管理" name="outband">
          <div style="margin-bottom:16px">
            <el-button type="primary" @click="loadSystemInfo" :loading="outbandLoading">获取系统信息</el-button>
            <el-button @click="loadSensors" :loading="outbandLoading">读取传感器</el-button>
            <el-button @click="loadFirmware" :loading="outbandLoading">固件清单</el-button>
          </div>
          <div v-if="powerState">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="电源状态"><el-tag :type="powerState.power_state === 'on' ? 'success' : 'danger'">{{ powerState.power_state }}</el-tag></el-descriptions-item>
            </el-descriptions>
            <div style="margin-top:12px">
              <el-button-group>
                <el-button type="success" size="small" @click="powerAction('on')">开机</el-button>
                <el-button type="danger" size="small" @click="powerAction('graceful_off')">关机</el-button>
                <el-button type="warning" size="small" @click="powerAction('restart')">重启</el-button>
              </el-button-group>
            </div>
          </div>
          <el-descriptions v-if="systemInfo" :column="2" border style="margin-top:16px">
            <el-descriptions-item label="制造商">{{ systemInfo.manufacturer || '-' }}</el-descriptions-item>
            <el-descriptions-item label="型号">{{ systemInfo.model || '-' }}</el-descriptions-item>
            <el-descriptions-item label="序列号">{{ systemInfo.serial_number || '-' }}</el-descriptions-item>
            <el-descriptions-item label="BIOS版本">{{ systemInfo.bios_version || '-' }}</el-descriptions-item>
          </el-descriptions>
          <el-table v-if="firmwareList.length" :data="firmwareList" stripe style="margin-top:16px" max-height="300">
            <el-table-column prop="component" label="固件名称" min-width="150" />
            <el-table-column prop="current_version" label="版本" width="150" />
            <el-table-column prop="available_version" label="可用版本" width="120" />
          </el-table>
          <el-table v-if="sensors.length" :data="sensors" stripe style="margin-top:16px" max-height="400">
            <el-table-column prop="name" label="传感器" min-width="150" />
            <el-table-column label="读数" width="120">
              <template #default="{ row }">{{ row.reading ?? '-' }} {{ row.unit }}</template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80" />
            <el-table-column prop="sensor_type" label="类型" width="100" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="监控指标" name="monitor">
          <p class="text-muted">请前往 <el-link type="primary" @click="$router.push('/monitor/dashboard')">监控概览</el-link> 查看详细指标</p>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { serverApi } from '@/api/asset'
import { outbandApi } from '@/api/outband-audit'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const serverId = route.params.id as string
const loading = ref(false)
const outbandLoading = ref(false)
const activeTab = ref('info')
const server = ref<any>({})
const powerState = ref<any>(null)
const sensors = ref<any[]>([])
const systemInfo = ref<any>(null)
const firmwareList = ref<any[]>([])

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await serverApi.get(serverId)
    server.value = data
  } catch { ElMessage.error('操作失败') } finally {
    loading.value = false
  }
})

async function loadSystemInfo() {
  outbandLoading.value = true
  try {
    const { data } = await outbandApi.getSystemInfo(serverId)
    systemInfo.value = data
    ElMessage.success('获取成功')
  } catch { ElMessage.error('操作失败') } finally {
    outbandLoading.value = false
  }
}

async function loadSensors() {
  outbandLoading.value = true
  try {
    const { data } = await outbandApi.getSensorData(serverId)
    sensors.value = data.sensors || []
    const { data: pd } = await outbandApi.getPowerState(serverId)
    powerState.value = pd
  } catch { ElMessage.error('操作失败') } finally {
    outbandLoading.value = false
  }
}

async function loadFirmware() {
  outbandLoading.value = true
  try {
    const { data } = await outbandApi.getFirmware(serverId)
    firmwareList.value = data.firmware || []
    ElMessage.success('获取成功')
  } catch { ElMessage.error('操作失败') } finally {
    outbandLoading.value = false
  }
}

async function powerAction(action: string) {
  const label: Record<string, string> = { on: '开机', graceful_off: '关机', restart: '重启' }
  try {
    await ElMessageBox.confirm(`确认执行${label[action] || action}操作？`, '电源操作', { type: 'warning' })
    await outbandApi.setPowerAction(serverId, action)
    ElMessage.success('操作成功')
    powerTimer = window.setTimeout(() => loadSensors(), 3000)
  } catch { ElMessage.error('操作失败') }
}

let powerTimer: number | null = null
onUnmounted(() => {
  if (powerTimer) {
    clearTimeout(powerTimer)
    powerTimer = null
  }
})
</script>

<style scoped>
.text-muted { color: #909399; }
</style>
