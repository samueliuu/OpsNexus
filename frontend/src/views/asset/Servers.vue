<template>
  <div>
    <Card>
      <template #content>
        <div class="page-header">
          <h3 class="page-title">服务器管理</h3>
          <div style="display:flex;gap:8px;align-items:center">
            <IconField>
              <InputIcon class="pi pi-search" />
              <InputText v-model="search" placeholder="搜索名称/序列号" style="width:200px" @keyup.enter="loadData" />
            </IconField>
            <Select v-model="filterBrand" :options="brands" placeholder="品牌" showClear style="width:120px" @change="page = 1; loadData()" />
            <Select v-model="filterStatus" :options="statusOptions" optionLabel="label" optionValue="value" placeholder="状态" showClear style="width:120px" @change="page = 1; loadData()" />
            <Button label="新增服务器" icon="pi pi-plus" @click="showDialog()" />
          </div>
        </div>
        <DataTable :value="tableData" stripedRows :loading="loading" style="cursor:pointer" @row-click="(e: any) => $router.push(`/asset/servers/${e.data.id}`)">
          <Column field="name" header="名称" style="min-width:120px" />
          <Column field="hostname" header="主机名" style="min-width:120px" />
          <Column field="brand" header="品牌" style="width:100px" />
          <Column field="model" header="型号" style="min-width:120px" />
          <Column header="状态" style="width:90px">
            <template #body="{ data }">
              <Tag :value="statusMap[data.status] || data.status" :severity="data.status === 'active' ? 'success' : data.status === 'maintenance' ? 'warning' : 'secondary'" />
            </template>
          </Column>
          <Column header="BMC" style="width:90px">
            <template #body="{ data }">
              <Tag :value="data.bmc_info?.bmc_status || '未知'" :severity="data.bmc_info?.bmc_status === 'online' ? 'success' : data.bmc_info?.bmc_status === 'offline' ? 'danger' : 'secondary'" />
            </template>
          </Column>
          <Column header="BMC IP" style="width:140px">
            <template #body="{ data }">{{ data.bmc_info?.bmc_ip || '-' }}</template>
          </Column>
          <Column header="CPU/内存" style="width:120px">
            <template #body="{ data }">{{ data.hardware_info?.cpu_count ?? '-' }}C / {{ data.hardware_info?.memory_gb ?? '-' }}G</template>
          </Column>
          <Column header="操作" style="width:150px" frozen alignFrozen="right">
            <template #body="{ data }">
              <Button label="编辑" link size="small" @click.stop="showDialog(data)" />
              <Button label="删除" link severity="danger" size="small" @click.stop="confirmDelete(data.id)" />
            </template>
          </Column>
        </DataTable>
        <Paginator :rows="pageSize" :totalRecords="total" :rowsPerPageOptions="[20, 50, 100]" @page="onPage" style="margin-top:16px" />
      </template>
    </Card>
    <Dialog v-model:visible="dialogVisible" :header="editingId ? '编辑服务器' : '新增服务器'" :style="{ width: '700px' }" modal destroyOnClose>
      <div class="p-fluid">
        <div class="form-grid">
          <div class="field">
            <label>名称 *</label>
            <InputText v-model="form.name" />
          </div>
          <div class="field">
            <label>主机名</label>
            <InputText v-model="form.hostname" />
          </div>
          <div class="field">
            <label>品牌 *</label>
            <Select v-model="form.brand" :options="brands" />
          </div>
          <div class="field">
            <label>型号 *</label>
            <InputText v-model="form.model" />
          </div>
          <div class="field">
            <label>BMC IP</label>
            <InputText v-model="form.bmc_info.bmc_ip" />
          </div>
          <div class="field">
            <label>状态</label>
            <Select v-model="form.status" :options="statusOptions" optionLabel="label" optionValue="value" />
          </div>
          <div class="field">
            <label>CPU型号</label>
            <InputText v-model="form.hardware_info.cpu_model" />
          </div>
          <div class="field">
            <label>CPU数量</label>
            <InputNumber v-model="form.hardware_info.cpu_count" :min="0" />
          </div>
          <div class="field">
            <label>内存(GB)</label>
            <InputNumber v-model="form.hardware_info.memory_gb" :min="0" />
          </div>
          <div class="field">
            <label>序列号</label>
            <InputText v-model="form.serial_number" />
          </div>
          <div class="field">
            <label>操作系统</label>
            <InputText v-model="form.software_info.os_name" />
          </div>
          <div class="field">
            <label>部门</label>
            <InputText v-model="form.department" />
          </div>
        </div>
      </div>
      <template #footer>
        <Button label="取消" severity="secondary" outlined @click="dialogVisible = false" />
        <Button label="确定" :loading="submitting" @click="handleSubmit" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { serverApi } from '@/api/asset'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Paginator from 'primevue/paginator'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'

const toast = useToast()
const confirm = useConfirm()
const brands = ['Dell', 'HPE', 'Lenovo', 'Huawei', 'Inspur', 'H3C', 'Sugon', 'xFusion']
const statusOptions = [
  { label: '运行中', value: 'active' },
  { label: '维护中', value: 'maintenance' },
  { label: '已下线', value: 'retired' },
]
const statusMap: Record<string, string> = { active: '运行中', inactive: '未激活', maintenance: '维护中', retired: '已下线' }

const loading = ref(false)
const tableData = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const search = ref('')
const filterBrand = ref('')
const filterStatus = ref('')

const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref('')

function emptyForm() {
  return {
    name: '', hostname: '', brand: 'Dell', model: '', status: 'active',
    serial_number: '', department: '',
    bmc_info: { bmc_ip: '' },
    hardware_info: { cpu_model: '', cpu_count: 0, memory_gb: 0 },
    software_info: { os_name: '', os_version: '' },
  }
}

const form = ref<any>(emptyForm())

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const params: any = { skip: (page.value - 1) * pageSize.value, limit: pageSize.value }
    if (search.value) params.search = search.value
    if (filterBrand.value) params.brand = filterBrand.value
    if (filterStatus.value) params.status = filterStatus.value
    const { data } = await serverApi.list(params)
    tableData.value = data.items || []
    total.value = data.total || 0
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '加载服务器失败', life: 3000 }) } finally {
    loading.value = false
  }
}

function onPage(event: any) {
  page.value = event.page + 1
  pageSize.value = event.rows
  loadData()
}

function showDialog(row?: any) {
  if (row) {
    editingId.value = row.id
    form.value = {
      name: row.name, hostname: row.hostname, brand: row.brand, model: row.model,
      status: row.status, serial_number: row.serial_number, department: row.department,
      bmc_info: { bmc_ip: row.bmc_info?.bmc_ip || '' },
      hardware_info: { cpu_model: row.hardware_info?.cpu_model || '', cpu_count: row.hardware_info?.cpu_count ?? 0, memory_gb: row.hardware_info?.memory_gb ?? 0 },
      software_info: { os_name: row.software_info?.os_name || '', os_version: row.software_info?.os_version || '' },
    }
  } else {
    editingId.value = ''
    form.value = emptyForm()
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!form.value.name || !form.value.brand || !form.value.model) {
    toast.add({ severity: 'warn', summary: '提示', detail: '请填写必填项', life: 3000 })
    return
  }
  submitting.value = true
  try {
    if (editingId.value) {
      await serverApi.update(editingId.value, form.value)
      toast.add({ severity: 'success', summary: '成功', detail: '更新成功', life: 2000 })
    } else {
      await serverApi.create(form.value)
      toast.add({ severity: 'success', summary: '成功', detail: '创建成功', life: 2000 })
    }
    dialogVisible.value = false
    loadData()
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '操作失败', life: 3000 }) } finally {
    submitting.value = false
  }
}

function confirmDelete(id: string) {
  confirm.require({
    message: '确认删除该服务器？',
    header: '确认',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: '删除',
    rejectLabel: '取消',
    accept: () => handleDelete(id),
  })
}

async function handleDelete(id: string) {
  try {
    await serverApi.delete(id)
    toast.add({ severity: 'success', summary: '成功', detail: '删除成功', life: 2000 })
    loadData()
  } catch { toast.add({ severity: 'error', summary: '错误', detail: '删除失败', life: 3000 }) }
}
</script>

<style scoped>
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}
.field { margin-bottom: 1rem; }
.field label { display: block; margin-bottom: 0.4rem; font-weight: 500; color: var(--text-secondary); font-size: 0.875rem; }
</style>
