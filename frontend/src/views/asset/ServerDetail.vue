<template>
  <div>
    <Card>
      <template #content>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h3 style="margin:0">服务器详情</h3>
          <Button label="返回" @click="$router.back()" />
        </div>
        <TabView v-model:activeIndex="activeTabIndex">
          <TabPanel header="基本信息" value="0">
            <div v-if="loading" style="text-align:center;padding:32px">
              <ProgressSpinner style="width:40px;height:40px" />
            </div>
            <div v-else class="desc-grid desc-grid-3">
              <div class="desc-item">
                <div class="desc-label">名称</div>
                <div class="desc-value">{{ server.name }}</div>
              </div>
              <div class="desc-item">
                <div class="desc-label">主机名</div>
                <div class="desc-value">{{ server.hostname }}</div>
              </div>
              <div class="desc-item">
                <div class="desc-label">品牌</div>
                <div class="desc-value">{{ server.brand }}</div>
              </div>
              <div class="desc-item">
                <div class="desc-label">型号</div>
                <div class="desc-value">{{ server.model }}</div>
              </div>
              <div class="desc-item">
                <div class="desc-label">序列号</div>
                <div class="desc-value">{{ server.serial_number }}</div>
              </div>
              <div class="desc-item">
                <div class="desc-label">状态</div>
                <div class="desc-value"><Tag :severity="server.status === 'active' ? 'success' : 'secondary'" style="font-size:12px">{{ server.status }}</Tag></div>
              </div>
              <div class="desc-item">
                <div class="desc-label">BMC IP</div>
                <div class="desc-value">{{ server.bmc_info?.bmc_ip || '-' }}</div>
              </div>
              <div class="desc-item">
                <div class="desc-label">BMC状态</div>
                <div class="desc-value"><Tag :severity="server.bmc_info?.bmc_status === 'online' ? 'success' : 'danger'" style="font-size:12px">{{ server.bmc_info?.bmc_status || '-' }}</Tag></div>
              </div>
              <div class="desc-item">
                <div class="desc-label">CPU</div>
                <div class="desc-value">{{ server.hardware_info?.cpu_model || '-' }} × {{ server.hardware_info?.cpu_count ?? '-' }}</div>
              </div>
              <div class="desc-item">
                <div class="desc-label">内存</div>
                <div class="desc-value">{{ server.hardware_info?.memory_gb ?? '-' }} GB</div>
              </div>
              <div class="desc-item">
                <div class="desc-label">操作系统</div>
                <div class="desc-value">{{ server.software_info?.os_name || '-' }} {{ server.software_info?.os_version || '' }}</div>
              </div>
              <div class="desc-item">
                <div class="desc-label">部门</div>
                <div class="desc-value">{{ server.department }}</div>
              </div>
            </div>
          </TabPanel>
          <TabPanel header="带外管理" value="1">
            <div style="margin-bottom:16px;display:flex;gap:8px">
              <Button label="获取系统信息" :loading="outbandLoading" @click="loadSystemInfo" />
              <Button label="读取传感器" :loading="outbandLoading" severity="secondary" @click="loadSensors" />
              <Button label="固件清单" :loading="outbandLoading" severity="secondary" @click="loadFirmware" />
            </div>
            <div v-if="powerState">
              <div class="desc-grid desc-grid-2">
                <div class="desc-item">
                  <div class="desc-label">电源状态</div>
                  <div class="desc-value"><Tag :severity="powerState.power_state === 'on' ? 'success' : 'danger'">{{ powerState.power_state }}</Tag></div>
                </div>
              </div>
              <div style="margin-top:12px;display:flex;gap:8px">
                <Button label="开机" severity="success" size="small" @click="powerAction('on')" />
                <Button label="关机" severity="danger" size="small" @click="powerAction('graceful_off')" />
                <Button label="重启" severity="warning" size="small" @click="powerAction('restart')" />
              </div>
            </div>
            <div v-if="systemInfo" class="desc-grid desc-grid-2" style="margin-top:16px">
              <div class="desc-item">
                <div class="desc-label">制造商</div>
                <div class="desc-value">{{ systemInfo.manufacturer || '-' }}</div>
              </div>
              <div class="desc-item">
                <div class="desc-label">型号</div>
                <div class="desc-value">{{ systemInfo.model || '-' }}</div>
              </div>
              <div class="desc-item">
                <div class="desc-label">序列号</div>
                <div class="desc-value">{{ systemInfo.serial_number || '-' }}</div>
              </div>
              <div class="desc-item">
                <div class="desc-label">BIOS版本</div>
                <div class="desc-value">{{ systemInfo.bios_version || '-' }}</div>
              </div>
            </div>
            <DataTable v-if="firmwareList.length" :value="firmwareList" stripedRows style="margin-top:16px" :scrollable="true" scrollHeight="300px">
              <Column field="component" header="固件名称" style="min-width:150px" />
              <Column field="current_version" header="版本" style="width:150px" />
              <Column field="available_version" header="可用版本" style="width:120px" />
            </DataTable>
            <DataTable v-if="sensors.length" :value="sensors" stripedRows style="margin-top:16px" :scrollable="true" scrollHeight="400px">
              <Column field="name" header="传感器" style="min-width:150px" />
              <Column header="读数" style="width:120px">
                <template #body="{ data }">{{ data.reading ?? '-' }} {{ data.unit }}</template>
              </Column>
              <Column field="status" header="状态" style="width:80px" />
              <Column field="sensor_type" header="类型" style="width:100px" />
            </DataTable>
          </TabPanel>
          <TabPanel header="监控指标" value="2">
            <p class="text-muted">请前往 <Button link label="监控概览" @click="$router.push('/monitor/dashboard')" /> 查看详细指标</p>
          </TabPanel>
        </TabView>
      </template>
    </Card>
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import Card from 'primevue/card'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'
import ConfirmDialog from 'primevue/confirmdialog'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { serverApi } from '@/api/asset'
import { outbandApi } from '@/api/outband-audit'

const route = useRoute()
const toast = useToast()
const confirm = useConfirm()
const serverId = route.params.id as string
const loading = ref(false)
const outbandLoading = ref(false)
const activeTabIndex = ref(0)
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
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 2000 })
  } finally {
    loading.value = false
  }
})

async function loadSystemInfo() {
  outbandLoading.value = true
  try {
    const { data } = await outbandApi.getSystemInfo(serverId)
    systemInfo.value = data
    toast.add({ severity: 'success', summary: '成功', detail: '获取成功', life: 2000 })
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 2000 })
  } finally {
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
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 2000 })
  } finally {
    outbandLoading.value = false
  }
}

async function loadFirmware() {
  outbandLoading.value = true
  try {
    const { data } = await outbandApi.getFirmware(serverId)
    firmwareList.value = data.firmware || []
    toast.add({ severity: 'success', summary: '成功', detail: '获取成功', life: 2000 })
  } catch {
    toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 2000 })
  } finally {
    outbandLoading.value = false
  }
}

function powerAction(action: string) {
  const label: Record<string, string> = { on: '开机', graceful_off: '关机', restart: '重启' }
  confirm.require({
    message: `确认执行${label[action] || action}操作？`,
    header: '电源操作',
    icon: 'pi pi-exclamation-triangle',
    accept: async () => {
      try {
        await outbandApi.setPowerAction(serverId, action)
        toast.add({ severity: 'success', summary: '成功', detail: '操作成功', life: 2000 })
        powerTimer = window.setTimeout(() => loadSensors(), 3000)
      } catch {
        toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 2000 })
      }
    }
  })
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
.text-muted { color: var(--text-color-secondary); }

.desc-grid {
  display: grid;
  border: 1px solid var(--surface-border);
  border-radius: 4px;
  overflow: hidden;
}
.desc-grid-3 {
  grid-template-columns: repeat(3, 1fr);
}
.desc-grid-2 {
  grid-template-columns: repeat(2, 1fr);
}
.desc-item {
  display: flex;
  flex-direction: column;
  border-bottom: 1px solid var(--surface-border);
  border-right: 1px solid var(--surface-border);
}
.desc-item:nth-last-child(-n + 3) {
  border-bottom: none;
}
.desc-grid-2 .desc-item:nth-last-child(-n + 2) {
  border-bottom: none;
}
.desc-item:last-child,
.desc-item:nth-child(3n) {
  border-right: none;
}
.desc-grid-2 .desc-item:nth-child(2n) {
  border-right: none;
}
.desc-label {
  background-color: var(--surface-hover);
  padding: 8px 12px;
  font-size: 13px;
  color: var(--text-muted);
  border-bottom: 1px solid var(--surface-border);
}
.desc-value {
  padding: 8px 12px;
  font-size: 14px;
  color: var(--text-color);
}
</style>
